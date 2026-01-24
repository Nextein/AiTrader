import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.config import settings
from app.core.analysis import AnalysisManager
import logging
import asyncio

logger = logging.getLogger("RiskAgent")

class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="RiskAgent")
        self.max_trade_size = settings.ORDER_SIZE_USDT
        
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
            logger.info("RiskAgent initialized in LIVE mode")

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
            logger.warning(f"Risk Rejected: Signal missing SL ({sl_price}) or TP ({tp_price})")
            return
            
        if not isinstance(sl_price, list): sl_price = [sl_price]
        if not isinstance(tp_price, list): tp_price = [tp_price]

        # Dynamic Position Sizing
        try:
            logger.info("Calculating dynamic position size...")
            
            # Use 1h for ATR calculation by default or the signal timeframe if provided
            tf = settings.TIMEFRAME
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            df = analysis_data.get("market_data", {}).get(tf)

            balance = await self.exchange.fetch_balance()
            if 'USDT' in balance and isinstance(balance['USDT'], dict):
                free_usdt = float(balance['USDT'].get('free', 0))
            elif 'free' in balance and 'USDT' in balance['free']:
                free_usdt = float(balance['free']['USDT'])
            else:
                free_usdt = float(balance.get('USDT', {}).get('free', 0))
            
            # Risk 2% of equity per trade
            risk_percent = 0.02 
            atr = self.calculate_atr(df)
            
            signal_price = data.get("price")
            if not signal_price or signal_price <= 0:
                if df is not None and not df.empty:
                    signal_price = float(df['Close'].iloc[-1])
                else:
                    logger.error("Risk Rejected: No price info available")
                    return
            
            if atr is not None and atr > 0:
                n_factor = 2
                raw_trade_size_usdt = (free_usdt * risk_percent) / (atr / signal_price * n_factor)
                max_size_cap = free_usdt * 0.1
                trade_size_usdt = min(raw_trade_size_usdt, max_size_cap) 
                logger.debug(f"Position Sizing | Size: {trade_size_usdt:.2f} USDT (ATR: {atr:.4f})")
            else:
                trade_size_usdt = self.max_trade_size
                logger.warning(f"ATR invalid. Using fallback static size: {trade_size_usdt}")

            
            if free_usdt < trade_size_usdt:
                logger.warning(f"Risk Rejected: Insufficient balance ({free_usdt:.2f} USDT < {trade_size_usdt:.2f} USDT)")
                return
                
            order_request = {
                "symbol": data.get("symbol"),
                "side": "buy" if data.get("signal") == "BUY" else "sell",
                "type": "market",
                "amount": trade_size_usdt / signal_price, # amount in base asset
                "price": signal_price,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "rationale": f"{data.get('rationale')} | Dynamic Size: {trade_size_usdt:.2f} USDT",
                "agent": self.name
            }
        except Exception as e:
            logger.error(f"Error calculating risk: {e}", exc_info=True)
            return

        logger.info(f"Risk Approved: {order_request['side']} {order_request['symbol']} size: {order_request['amount']:.6f} ({trade_size_usdt:.2f} USDT)")
        await event_bus.publish(EventType.ORDER_REQUEST, order_request)

    async def stop(self):
        await super().stop()
        # Only close if it's a real exchange connection (demo_engine close is a stub)
        if hasattr(self.exchange, 'close'):
            await self.exchange.close()

import asyncio
