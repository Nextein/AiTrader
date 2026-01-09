import ccxt.async_support as ccxt
import pandas as pd
import pandas_ta as ta
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.config import settings
import logging

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

    async def run_loop(self):
        event_bus.subscribe(EventType.SIGNAL, self.on_signal)
        event_bus.subscribe(EventType.MARKET_DATA, self.on_market_data)
        self.latest_candles = None
        while self.is_running:
            await asyncio.sleep(1)

    async def on_market_data(self, data):
        self.latest_candles = data.get("candles")

    def calculate_atr(self, candles, period=14):
        if not candles or len(candles) < period + 1:
            return None
        df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        atr = df.ta.atr(length=period)
        if atr is None or atr.empty:
            return None
        val = atr.iloc[-1]
        return float(val) if pd.notnull(val) else None

    async def on_signal(self, data):
        if not self.is_running:
            return

        # Basic risk validation
        if data.get("confidence", 0) < 0.6:
            logger.info(f"Signal rejected: Confidence too low ({data.get('confidence')})")
            return

        # Dynamic Position Sizing
        try:
            logger.info("Calculating dynamic position size...")
            balance = await self.exchange.fetch_balance()
            
            # Robust balance extraction supporting CCXT, BingX info, and Repo fallback
            if 'USDT' in balance and isinstance(balance['USDT'], dict):
                free_usdt = float(balance['USDT'].get('free', 0))
            elif 'free' in balance and 'USDT' in balance['free']:
                free_usdt = float(balance['free']['USDT'])
            elif 'info' in balance and 'data' in balance['info'] and 'balance' in balance['info']['data']:
                free_usdt = float(balance['info']['data']['balance'])
            else:
                # Last resort: try direct 'USDT' if it was a flat float (unlikely in CCXT but for safety)
                free_usdt = float(balance.get('USDT', 0))
            
            # Risk 2% of equity per trade, adjusted by ATR
            risk_percent = 0.02 
            atr = self.calculate_atr(self.latest_candles)
            
            # Fallback for price if missing or zero
            signal_price = data.get("price")
            if not signal_price or signal_price <= 0:
                if self.latest_candles and len(self.latest_candles) > 0:
                    signal_price = self.latest_candles[-1][4] # Last Close
                else:
                    logger.error("Risk Rejected: No price info available for calculation")
                    return

            if atr is not None and atr > 0:
                # Formula: Size = (Equity * Risk%) / (ATR * N)
                # Here N=2 for a 2x ATR stop distance buffer
                n_factor = 2
                trade_size_usdt = (free_usdt * risk_percent) / (atr / signal_price * n_factor)
                trade_size_usdt = min(trade_size_usdt, free_usdt * 0.1) # Max 10% of balance per trade
            else:
                trade_size_usdt = self.max_trade_size # Fallback
            
            if free_usdt < trade_size_usdt:
                logger.warning(f"Risk Rejected: Insufficient balance ({free_usdt:.2f} USDT < {trade_size_usdt:.2f} USDT)")
                return
                
            order_request = {
                "symbol": data.get("symbol"),
                "side": "buy" if data.get("signal") == "BUY" else "sell",
                "type": "market",
                "amount": trade_size_usdt / signal_price, # amount in base asset
                "price": signal_price,
                "rationale": f"{data.get('rationale')} | Dynamic Size: {trade_size_usdt:.2f} USDT",
                "agent": self.name
            }
        except Exception as e:
            logger.error(f"Error calculating risk: {e}")
            return

        logger.info(f"Risk Approved: {order_request['side']} {order_request['symbol']} size: {order_request['amount']:.6f} ({trade_size_usdt:.2f} USDT)")
        await event_bus.publish(EventType.ORDER_REQUEST, order_request)

    async def stop(self):
        await super().stop()
        # Only close if it's a real exchange connection (demo_engine close is a stub)
        if hasattr(self.exchange, 'close'):
            await self.exchange.close()

import asyncio
