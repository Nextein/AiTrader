import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.config import settings
from app.core.analysis import AnalysisManager
import logging
import asyncio
from typing import Dict, Any, List, Optional

logger = logging.getLogger("RiskAgent")

class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="RiskAgent")
        self.max_trade_size = settings.ORDER_SIZE_USDT
        self.risk_per_trade = 0.01 # 1% default
        self.max_portfolio_drawdown = 0.05 # 5% max drawdown
        
        # Use demo engine or live BingX based on DEMO_MODE
        if settings.DEMO_MODE:
            from app.core.demo_engine import demo_engine
            self.exchange = demo_engine
            logger.info("RiskAgent initialized in DEMO mode")
        else:
            self.exchange = ccxt.bingx({
                'apiKey': settings.BINGX_API_KEY,
                'secret': settings.BINGX_SECRET_KEY,
                'options': {
                    'defaultType': 'swap',
                    'sandbox': settings.BINGX_IS_SANDBOX,
                }
            })
            self.log("RiskAgent initialized in LIVE mode", level="INFO")

        self.last_ts = {} # {symbol_tf: ts}

    async def run_loop(self):
        event_bus.subscribe(EventType.SIGNAL, self.on_signal)
        event_bus.subscribe(EventType.MARKET_DATA, self.on_market_data)
        while self.is_running:
            await asyncio.sleep(1)

    async def on_market_data(self, data):
        # We just track that we got new data
        symbol = data.get("symbol")
        tf = data.get("timeframe", "1h")
        self.last_ts[f"{symbol}_{tf}"] = data.get("timestamp")

    # ATR calculation updated to use DataFrames
    def calculate_atr(self, df, period=14):
        if df is None or not isinstance(df, pd.DataFrame) or len(df) < period + 1:
            return None
        
        # We look for predefined ATR if MarketDataAgent added it
        if 'Average True Range' in df.columns:
            val = df['Average True Range'].iloc[-1]
        else:
            # Fallback
            atr = df.ta.atr(length=period)
            if atr is None or atr.empty: return None
            val = atr.iloc[-1]
        
        return float(val) if pd.notnull(val) else None

    async def on_signal(self, data):
        if not self.is_running:
            return

        symbol = data.get("symbol")
        logger.info(f"RiskAgent received Signal: {data.get('signal')} {symbol}")

        # Basic risk validation
        if data.get("confidence", 0) < 0.6:
            logger.info(f"Signal rejected: Confidence too low ({data.get('confidence')})")
            return

        sl_price = data.get("sl_price")
        tp_price = data.get("tp_price")
        if sl_price is None or tp_price is None:
            self.log(f"Risk Rejected: Signal missing SL ({sl_price}) or TP ({tp_price})", level="WARNING")
            return
            
        if not isinstance(sl_price, list): sl_price = [sl_price]
        if not isinstance(tp_price, list): tp_price = [tp_price]

        # 1. Fetch Balance and Portfolio stats
        balance = await self.exchange.fetch_balance()
        free_usdt = self._extract_free_usdt(balance)

        # Confidence-based multiplier (0.6 to 1.0 -> 0.5x to 1.2x)
        confidence = data.get("confidence", 0.7)
        conf_multiplier = (confidence - 0.5) * 2
        conf_multiplier = max(0.5, min(1.2, conf_multiplier))

        # Dynamic Position Sizing (ATR based)
        try:
            tf = settings.TIMEFRAME
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            df = analysis_data.get("market_data", {}).get(tf)

            atr = self.calculate_atr(df)
            signal_price = data.get("price") or (df['Close'].iloc[-1] if df is not None else 0)

            if atr and atr > 0:
                # Sizing formula: (Equity * Risk%) / (StopDistance)
                # We use 1.5 * ATR as stop distance if not provided
                sl_dist = abs(signal_price - sl_price[0]) if sl_price else (1.5 * atr)
                raw_size_usdt = (free_usdt * self.risk_per_trade * conf_multiplier) / (sl_dist / signal_price)

                # Caps
                max_size = free_usdt * 0.2 # Max 20% of account in one position
                trade_size_usdt = min(raw_size_usdt, max_size, self.max_trade_size)
            else:
                trade_size_usdt = self.max_trade_size * conf_multiplier

            if free_usdt < trade_size_usdt:
                logger.warning(f"Risk Rejected: Insufficient balance {free_usdt} for size {trade_size_usdt}")
                return

            order_request = {
                "symbol": data.get("symbol"),
                "side": "buy" if data.get("signal") == "BUY" else "sell",
                "type": "market",
                "amount": float(trade_size_usdt / signal_price),
                "price": signal_price,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "confidence": confidence,
                "rationale": f"{data.get('rationale')} | Conf: {confidence:.2f} | Size: {trade_size_usdt:.2f} USDT",
                "agent": self.name
            }
        except Exception as e:
            logger.error(f"Error calculating risk: {e}", exc_info=True)
            return

        self.log(f"Risk Approved: {order_request['side']} {order_request['symbol']} size: {order_request['amount']:.6f}", level="INFO")
        await event_bus.publish(EventType.ORDER_REQUEST, order_request)

    async def stop(self):
        await super().stop()
        # Only close if it's a real exchange connection (demo_engine close is a stub)
        if hasattr(self.exchange, 'close'):
            await self.exchange.close()

    def _extract_free_usdt(self, balance: Dict) -> float:
        if 'USDT' in balance and isinstance(balance['USDT'], dict):
            return float(balance['USDT'].get('free', 0))
        if 'free' in balance and 'USDT' in balance['free']:
            return float(balance['free']['USDT'])
        return float(balance.get('USDT', {}).get('free', 0))
