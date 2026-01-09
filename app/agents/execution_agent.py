import asyncio
import ccxt.async_support as ccxt
from app.agents.base_agent import BaseAgent
from app.core.config import settings
from app.core.event_bus import event_bus, EventType
import logging

logger = logging.getLogger("ExecutionAgent")

class ExecutionAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="ExecutionAgent")
        self.exchange = ccxt.bingx({
            'apiKey': settings.BINGX_API_KEY,
            'secret': settings.BINGX_SECRET_KEY,
            'options': {
                'defaultType': 'swap',
                'sandbox': settings.BINGX_IS_SANDBOX,
            }
        })

    async def run_loop(self):
        event_bus.subscribe(EventType.ORDER_REQUEST, self.on_order_request)
        while self.is_running:
            await asyncio.sleep(1)

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
            
            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount
            )
            
            logger.info(f"ORDER FILLED: {order['id']} | {side.upper()} {amount} {symbol}")
            order["agent"] = self.name
            await event_bus.publish(EventType.ORDER_FILLED, order)
            
        except Exception as e:
            logger.error(f"Execution Error: {e}")
            await event_bus.publish(EventType.ERROR, {"agent": self.name, "error": str(e)})

    async def stop(self):
        await super().stop()
        await self.exchange.close()
