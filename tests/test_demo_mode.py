import asyncio
import unittest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from app.core.config import settings
from app.core.database import SessionLocal, engine, Base
from app.models.models import OrderModel, DemoBalanceModel, EquityModel
from app.agents.execution_agent import ExecutionAgent
from app.agents.governor_agent import GovernorAgent
from app.core.event_bus import event_bus, EventType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestDemoMode(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Force DEMO_MODE for tests
        settings.DEMO_MODE = True
        
        # Use a separate test database file
        self.test_db_path = "test_trading_bot.db"
        self.test_db_url = f"sqlite:///./{self.test_db_path}"
        self.test_engine = create_engine(self.test_db_url, connect_args={"check_same_thread": False})
        self.TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.test_engine)
        
        Base.metadata.drop_all(bind=self.test_engine)
        Base.metadata.create_all(bind=self.test_engine)
        
        # Patch the database connections in the app
        self.patchers = [
            patch('app.core.database.engine', self.test_engine),
            patch('app.core.database.SessionLocal', self.TestSessionLocal),
            patch('app.agents.governor_agent.SessionLocal', self.TestSessionLocal),
            patch('app.core.demo_engine.SessionLocal', self.TestSessionLocal),
            patch('app.agents.market_data_agent.SessionLocal', self.TestSessionLocal),
        ]
        for p in self.patchers:
            p.start()

    async def asyncTearDown(self):
        for p in self.patchers:
            p.stop()
        
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except PermissionError:
                pass # Might be locked by some async process

    async def test_demo_engine_initialization(self):
        governor = GovernorAgent()
        # Mock ccxt to avoid network calls during agent init
        with patch('ccxt.async_support.bingx', return_value=AsyncMock()):
            await governor.start()
            await asyncio.sleep(0.5) # Wait for agents to subscribe
            
            with self.TestSessionLocal() as db:
                balance = db.query(DemoBalanceModel).first()
                self.assertIsNotNone(balance)
                self.assertEqual(balance.balance, settings.INITIAL_DEMO_BALANCE)
            
            await governor.stop()

    async def test_execution_agent_demo_trade(self):
        governor = GovernorAgent()
        with patch('ccxt.async_support.bingx', return_value=AsyncMock()):
            await governor.start()
            await asyncio.sleep(0.5) # Wait for agents to subscribe
            
            exec_agent = next(a for a in governor.agents if a.name == "ExecutionAgent")
            
            # Simulate Market Data to set price
            await event_bus.publish(EventType.MARKET_DATA, {
                "symbol": "BTC-USDT",
                "latest_close": 50000.0,
                "timeframe": "1m",
                "candles": [],
                "timestamp": 123456789,
                "agent": "MarketDataAgent"
            })
            
            # Wait for ExecutionAgent to process market data
            for _ in range(20):
                if exec_agent.latest_prices.get("BTC-USDT") == 50000.0:
                    break
                await asyncio.sleep(0.1)
            
            self.assertEqual(exec_agent.latest_prices.get("BTC-USDT"), 50000.0)
            
            # Request Order
            order_data = {
                "symbol": "BTC-USDT",
                "side": "buy",
                "amount": 0.01 # 500 USDT
            }
            
            await event_bus.publish(EventType.ORDER_REQUEST, order_data)
            await asyncio.sleep(0.5)
            
            # Verify Results
            with self.TestSessionLocal() as db:
                order = db.query(OrderModel).filter(OrderModel.is_demo == 1).first()
                self.assertIsNotNone(order)
                self.assertEqual(order.price, 50000.0)
                
                balance = db.query(DemoBalanceModel).first()
                expected_balance = settings.INITIAL_DEMO_BALANCE - (0.01 * 50000.0)
                self.assertEqual(balance.balance, expected_balance)

            await governor.stop()

    async def test_equity_snapshot_demo(self):
        governor = GovernorAgent()
        governor.is_running = True # Must be running for the loop to work
        with patch('ccxt.async_support.bingx', return_value=AsyncMock()):
            # Mock sleep to run loop once and exit
            with patch('asyncio.sleep', side_effect=[None, asyncio.CancelledError]):
                try:
                    await governor.equity_snapshot_loop()
                except (asyncio.CancelledError, Exception):
                    pass
                
            with self.TestSessionLocal() as db:
                snapshot = db.query(EquityModel).first()
                self.assertIsNotNone(snapshot)
                self.assertEqual(snapshot.total_equity, settings.INITIAL_DEMO_BALANCE)
        governor.is_running = False

if __name__ == "__main__":
    unittest.main()
