import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.agents.risk_agent import RiskAgent
from app.core.demo_engine import DemoEngine
from app.models.models import OrderModel
from app.core.event_bus import event_bus, EventType

from app.core.config import settings

class TestSLTPLogic(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Force Demo Mode
        self.original_demo_mode = settings.DEMO_MODE
        settings.DEMO_MODE = True

        # In-memory DB for testing
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        
    async def asyncTearDown(self):
        settings.DEMO_MODE = self.original_demo_mode
        self.db.close()
        event_bus.clear_subscribers()


    async def test_risk_agent_enforces_sl_tp(self):
        risk_agent = RiskAgent()
        risk_agent.is_running = True # REQUIRED for on_signal to process
        
        # Test valid signal
        valid_signal = {
            "symbol": "BTC/USDT",
            "signal": "BUY",
            "confidence": 0.9,
            "sl_price": 50000,
            "tp_price": 60000,
            "price": 55000,
            "timestamp": datetime.now().isoformat()
        }
        
        received_orders = []
        async def capture_order(event):
            received_orders.append(event)
        
        event_bus.subscribe(EventType.ORDER_REQUEST, capture_order)
        
        # We need to mock fetch_balance for RiskAgent validation if it calls it
        # RiskAgent.on_signal calls validate_risk -> check_drawdown -> demo_engine.fetch_balance
        with patch('app.core.demo_engine.demo_engine.fetch_balance', new_callable=AsyncMock) as mock_bal:
            mock_bal.return_value = {'total': {'USDT': 1000}, 'free': {'USDT': 1000}}
            
            await risk_agent.on_signal(valid_signal)
            
            # Wait for event bus (async background task)
            await asyncio.sleep(0.5)
            
            self.assertEqual(len(received_orders), 1)
            self.assertEqual(received_orders[0]["sl_price"], [50000]) # Normalized to list
            self.assertEqual(received_orders[0]["tp_price"], [60000])

            # Test invalid signal (missing SL/TP)
            invalid_signal = {
                "symbol": "BTC/USDT",
                "signal": "BUY",
                "confidence": 0.9,
                "price": 55000,
                "timestamp": datetime.now().isoformat()
            }
            
            received_orders.clear()
            await risk_agent.on_signal(invalid_signal)
            self.assertEqual(len(received_orders), 0) # Should be rejected

    async def test_demo_engine_sl_hit(self):
        # We need to inject the db session into DemoEngine
        # DemoEngine uses SessionLocal by default. We should patch it or pass it if possible.
        # DemoEngine init: self.db = db_session or SessionLocal()
        
        demo = DemoEngine(db_session=self.db)
        await demo.initialize_balance()
        
        # Create an order
        await demo.create_order(
            symbol="BTC/USDT",
            type="market",
            side="buy",
            amount=1.0,
            price=55000.0,
            params={"sl_price": [54000.0], "tp_price": [60000.0]}
        )
        
        # Verify order is created
        order = self.db.query(OrderModel).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "FILLED")
        self.assertIsNone(order.closed_at)
        
        # Simulate market data hitting SL
        market_data = {
            "symbol": "BTC/USDT",
            "latest_close": 53900.0, # Below SL
            "timestamp": datetime.now()
        }
        
        await demo.check_sl_tp(market_data)
        
        # Verify order is closed
        self.db.refresh(order)
        self.assertEqual(order.status, "CLOSED")
        self.assertEqual(order.exit_price, 53900.0) # Market Order execution at trigger time
        self.assertIn("Stop Loss Hit", order.rationale)
        self.assertTrue(order.pnl < 0)

    async def test_demo_engine_tp_hit(self):
        demo = DemoEngine(db_session=self.db)
        await demo.initialize_balance()
        
        # Create an order
        await demo.create_order(
            symbol="ETH/USDT",
            type="market",
            side="buy",
            amount=10.0,
            price=3000.0,
            params={"sl_price": [2900.0], "tp_price": [3100.0]}
        )
        
        # Simulate market data hitting TP
        market_data = {
            "symbol": "ETH/USDT",
            "latest_close": 3150.0, # Above TP
            "timestamp": datetime.now()
        }
        
        await demo.check_sl_tp(market_data)
        
        # Verify order is closed
        order = self.db.query(OrderModel).filter(OrderModel.symbol == "ETH/USDT").first()
        self.assertEqual(order.status, "CLOSED")
        self.assertEqual(order.exit_price, 3150.0) # Market Order execution at trigger time
        self.assertIn("Take Profit Hit", order.rationale)
        self.assertTrue(order.pnl > 0)
