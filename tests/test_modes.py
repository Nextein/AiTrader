import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from app.core.config import settings
from app.agents.risk_agent import RiskAgent
from app.agents.execution_agent import ExecutionAgent
from app.core.database import SessionLocal, Base, engine
from app.models.models import OrderModel
from app.core.event_bus import event_bus, EventType

class TestModesIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_demo_mode = settings.DEMO_MODE
        # Setup clean DB for each test if needed, or use mocks
        Base.metadata.create_all(bind=engine)

    async def asyncTearDown(self):
        settings.DEMO_MODE = self.original_demo_mode
        event_bus.clear_subscribers()

    async def test_demo_mode_flag_in_orders(self):
        """Verify that orders created in demo mode have is_demo=1."""
        settings.DEMO_MODE = True
        
        # We need to mock the demo_engine to avoid actual DB writes during the agent call if we want pure unit, 
        # but here we want to see it serialized.
        # Actually, ExecutionAgent uses self.exchange.create_order
        
        with patch('app.core.demo_engine.demo_engine.create_order', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {
                "id": "demo-order-123",
                "symbol": "BTC-USDT",
                "side": "buy",
                "amount": 0.1,
                "price": 50000.0,
                "status": "filled",
                "is_demo": 1
            }
            
            exec_agent = ExecutionAgent()
            exec_agent.is_running = True
            exec_agent.latest_prices["BTC-USDT"] = 50000.0
            
            with patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock) as mock_pub:
                await exec_agent.on_order_request({
                    "symbol": "BTC-USDT",
                    "side": "buy",
                    "amount": 0.1
                })
                
                # Check that the published event has is_demo=1
                mock_pub.assert_called()
                args, _ = mock_pub.call_args
                event_type, order_data = args
                self.assertEqual(order_data["is_demo"], 1)

    async def test_live_mode_init_failure_protection(self):
        """Ensure live mode initialization doesn't happen accidentally in tests."""
        settings.DEMO_MODE = False
        settings.BINGX_API_KEY = "dummy"
        settings.BINGX_SECRET_KEY = "dummy"
        
        # Test that ExecutionAgent in live mode attempts to use ccxt.bingx
        with patch('ccxt.async_support.bingx') as mock_bingx:
            ExecutionAgent()
            mock_bingx.assert_called()

    @patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock)
    async def test_risk_agent_approved_flow_demo(self, mock_pub):
        """Test full flow from RiskAgent approval to Order Request in Demo mode."""
        settings.DEMO_MODE = True
        risk_agent = RiskAgent()
        risk_agent.is_running = True
        risk_agent.latest_candles = [[i, 50000, 50000, 50000, 50000, 10] for i in range(20)]
        
        # Mock balance
        from app.core.demo_engine import demo_engine
        demo_engine.fetch_balance = AsyncMock(return_value={'USDT': {'free': 1000.0}})
        
        signal = {
            "symbol": "BTC-USDT",
            "signal": "BUY",
            "confidence": 0.9,
            "price": 50000,
            "rationale": "Test"
        }
        
        await risk_agent.on_signal(signal)
        
        # Should publish ORDER_REQUEST
        mock_pub.assert_called()
        args, _ = mock_pub.call_args
        event_type, order_request = args
        self.assertEqual(event_type, EventType.ORDER_REQUEST)
        self.assertEqual(order_request["symbol"], "BTC-USDT")

if __name__ == "__main__":
    unittest.main()
