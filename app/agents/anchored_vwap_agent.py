import pandas as pd
import numpy as np
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C

logger = logging.getLogger("AnchoredVWAPAgent")

class AnchoredVWAPAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="AnchoredVWAPAgent")
        self.last_processed = {} # {symbol_tf: timestamp}

    async def run_loop(self):
        event_bus.subscribe(EventType.ANALYSIS_UPDATE, self.handle_analysis_update)
        while self.is_running:
            await asyncio.sleep(1)

    async def handle_analysis_update(self, data: Dict[str, Any]):
        if not self.is_running or not self.is_active:
            return
            
        if data.get("section") != "market_structure":
            return
            
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        
        if not symbol or not timeframe:
            return

        try:
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            
            df = analysis_data.get("market_data", {}).get(timeframe)
            if df is None or len(df) < 60:
                return
                
            ts = df['timestamp'].iloc[-1]
            lookup_key = f"{symbol}_{timeframe}"
            if self.last_processed.get(lookup_key) == ts:
                return
            self.last_processed[lookup_key] = ts

            # 1. Identify Anchor Point (Major Swing High/Low in last 200 bars)
            lookback = min(len(df), 200)
            subset = df.iloc[-lookback:]
            
            # Simple heuristic: anchor to the absolute high or low of the lookback
            anchor_idx_high = subset['High'].idxmax()
            anchor_idx_low = subset['Low'].idxmin()
            
            # We'll calculate for both or pick the most 'significant' one (furthest back)
            anchors = [anchor_idx_high, anchor_idx_low]
            
            vwaps = []
            for anchor in anchors:
                vwap_series = self._calculate_anchored_vwap(df, anchor)
                if not vwap_series.empty:
                    # 2. Gaussian Process Projection
                    projection = self._project_vwap(vwap_series)
                    vwaps.append({
                        "id": f"vwap_{anchor}",
                        "anchor_price": float(df.loc[anchor, 'High' if anchor == anchor_idx_high else 'Low']),
                        "anchor_time": int(df.loc[anchor, 'timestamp']),
                        "current_val": float(vwap_series.iloc[-1]),
                        "projection": projection
                    })

            # 3. Update Analysis Object
            avwap_data = {
                "vwaps": vwaps,
                "last_updated": int(time.time())
            }
            
            await analysis.update_section("anchored_vwap", avwap_data, timeframe)
            
            self.processed_count += 1
            logger.info(f"Updated Anchored VWAP analysis for {symbol} {timeframe}")

        except Exception as e:
            logger.error(f"Error in AnchoredVWAPAgent for {symbol}: {e}", exc_info=True)

    def _calculate_anchored_vwap(self, df: pd.DataFrame, anchor_idx: Any) -> pd.Series:
        """Calculates VWAP starting from anchor_idx"""
        try:
            # We need standard OHLCV columns
            # Calculate from anchor to end
            start_idx = df.index.get_loc(anchor_idx)
            working_df = df.iloc[start_idx:].copy()
            
            typical_price = (working_df['High'] + working_df['Low'] + working_df['Close']) / 3
            pv = typical_price * working_df['Volume']
            
            vwap = pv.cumsum() / working_df['Volume'].cumsum()
            return vwap
        except Exception as e:
            logger.error(f"VWAP Calc Error: {e}")
            return pd.Series()

    def _project_vwap(self, vwap_series: pd.Series, periods: int = 10) -> List[float]:
        """Uses GP to project the next N periods of VWAP"""
        try:
            if len(vwap_series) < 10: return []
            
            # Use last 30 values for training
            train_data = vwap_series.tail(30)
            X = np.arange(len(train_data)).reshape(-1, 1)
            y = train_data.values.reshape(-1, 1)
            
            # Simple GP kernel
            kernel = C(1.0, (1e-3, 1e3)) * RBF(10, (1e-2, 1e2))
            gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=3)
            
            gp.fit(X, y)
            
            # Predict future
            X_pred = np.arange(len(train_data), len(train_data) + periods).reshape(-1, 1)
            y_pred, sigma = gp.predict(X_pred, return_std=True)
            
            return [float(v) for v in y_pred.flatten()]
        except Exception as e:
            logger.error(f"GP Projection Error: {e}")
            return []
