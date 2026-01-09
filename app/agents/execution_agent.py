import asyncio
import ccxt.async_support as ccxt
from app.agents.base_agent import BaseAgent
from app.core.config import settings
from app.core.event_bus import event_bus, EventType
from app.core.database import SessionLocal
from app.models.models import OrderModel
from datetime import datetime, timezone
import logging

logger = logging.getLogger("ExecutionAgent")

class ExecutionAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="ExecutionAgent")
        self.latest_prices = {}
        if settings.DEMO_MODE:
            from app.core.demo_engine import demo_engine
            self.exchange = demo_engine
            logger.info("ExecutionAgent: Running in DEMO MODE")
        else:
            self.exchange = ccxt.bingx({
                'apiKey': settings.BINGX_API_KEY,
                'secret': settings.BINGX_SECRET_KEY,
                'options': {
                    'defaultType': 'swap',
                    'sandbox': settings.BINGX_IS_SANDBOX,
                }
            })
            logger.info("ExecutionAgent: Running in LIVE/SANDBOX MODE")

    async def run_loop(self):
        event_bus.subscribe(EventType.ORDER_REQUEST, self.on_order_request)
        event_bus.subscribe(EventType.EMERGENCY_EXIT, self.on_emergency_exit)
        event_bus.subscribe(EventType.MARKET_DATA, self.on_market_data)
        while self.is_running:
            await asyncio.sleep(1)

    async def on_market_data(self, data):
        self.latest_prices[data['symbol']] = data['latest_close']
        
        # Task 5: Trigger Demo Engine SL/TP check if in Demo Mode
        if settings.DEMO_MODE and hasattr(self.exchange, 'check_sl_tp'):
            await self.exchange.check_sl_tp(data)

    async def on_emergency_exit(self, data):
        logger.warning("ExecutionAgent: EMERGENCY EXIT RECEIVED. CLOSING ALL POSITIONS.")
        try:
            # 1. Cancel all open orders
            # BingX swap order cancellation
            await self.exchange.cancel_all_orders()
            logger.info("Emergency: All open orders cancelled.")

            # 2. Close all positions
            # For simplicity in MVP, we fetch positions and market close them
            # This is exchange-specific. In BingX CCXT, we might need to iterate.
            balances = await self.exchange.fetch_balance()
            # In swap accounts, 'total' might show positions. 
            # This is complex across different ccxt implementations.
            # Most robust way is to fetch positions and close each.
            positions = await self.exchange.fetch_positions()
            for pos in positions:
                contracts = float(pos['contracts'])
                if contracts != 0:
                    side = 'sell' if float(pos['contracts']) > 0 else 'buy'
                    symbol = pos['symbol']
                    logger.warning(f"Emergency: Closing position {symbol} volume {contracts}")
                    await self.exchange.create_order(
                        symbol=symbol,
                        type='market',
                        side=side,
                        amount=abs(contracts),
                        params={'reduceOnly': True}
                    )
            logger.info("Emergency: All positions close commands issued.")
        except Exception as e:
            logger.error(f"Emergency Closure Error: {e}")

    async def on_order_request(self, data):
        if not self.is_running:
            return

        try:
            logger.info(f"Executing Order: {data['side']} {data['symbol']} {data['amount']}")
            
            # Real execution (In MVP, we should check exchange status etc)
            # symbol mapping for bingx might need adjustment depending on ccxt version
            symbol = data['symbol']
            side = data['side']
            amount = data['amount']
            
            # For demo mode, we need to pass the price since it's a simulation
            price = self.latest_prices.get(symbol, 0.0) if settings.DEMO_MODE else None
            
            # Extract SL/TP/Rationale
            sl_price = data.get('sl_price')
            tp_price = data.get('tp_price')
            rationale = data.get('rationale')
            
            params = {
                'sl_price': sl_price,
                'tp_price': tp_price,
                'rationale': rationale
            }
            
            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                price=price,
                params=params
            )
            
            # Persist to DB if LIVE mode (DemoEngine does it internally)
            if not settings.DEMO_MODE:
                with SessionLocal() as db:
                    db_order = OrderModel(
                        exchange_order_id=str(order.get('id', 'unknown')),
                        symbol=symbol,
                        side=side,
                        order_type='market',
                        amount=amount,
                        price=order.get('price', price), # Use filled price if avail
                        sl_price=sl_price,
                        tp_price=tp_price,
                        rationale=rationale,
                        status=order.get('status', 'OPEN'),
                        is_demo=0,
                        timestamp=datetime.now(timezone.utc)
                    )
                    db.add(db_order)
                    db.commit()
            
            logger.info(f"ORDER FILLED: {order['id']} | {side.upper()} {amount} {symbol}")
            order["agent"] = self.name
            await event_bus.publish(EventType.ORDER_FILLED, order)
            
        except Exception as e:
            logger.error(f"Execution Error: {e}")
            await event_bus.publish(EventType.ERROR, {"agent": self.name, "error": str(e)})

    async def stop(self):
        await super().stop()
        await self.exchange.close()
