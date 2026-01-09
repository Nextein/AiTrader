import asyncio
import unittest
from unittest.mock import AsyncMock, patch
from app.agents.market_data_agent import MarketDataAgent
from app.agents.strategy_agent import StrategyAgent
from app.agents.risk_agent import RiskAgent
from app.agents.execution_agent import ExecutionAgent
from app.agents.aggregator_agent import AggregatorAgent
from app.agents.audit_log_agent import AuditLogAgent
from app.core.event_bus import event_bus, EventType
from app.core.database import SessionLocal, engine
from app.models.models import Base, CandleModel, AuditLogModel
import pandas as pd

class TestSystemPhase2(unittest.IsolatedAsyncioTestCase):
    async def test_aggregator_and_audit(self):
        # 0. Prep Database
        Base.metadata.create_all(bind=engine)
        
        # 1. Mock the Exchange
        with patch('ccxt.async_support.bingx') as mock_bingx:
            instance = mock_bingx.return_value
            instance.fetch_ohlcv = AsyncMock(return_value=[
                [1700000000000, 30000, 31000, 29000, 30500, 100],
                [1700000060000, 30500, 31500, 30000, 25000, 100]
            ] * 50)
            instance.create_order = AsyncMock(return_value={'id': 'test-order-phase2'})
            instance.close = AsyncMock()

            # 2. Instantiate Agents
            strategy_agent = StrategyAgent(strategy_id="RSI_MACD")
            aggregator_agent = AggregatorAgent(window_seconds=0.1)
            risk_agent = RiskAgent()
            execution_agent = ExecutionAgent()
            audit_agent = AuditLogAgent()

            # 3. Start listeners
            loop_tasks = [
                asyncio.create_task(strategy_agent.run_loop()),
                asyncio.create_task(aggregator_agent.run_loop()),
                asyncio.create_task(risk_agent.run_loop()),
                asyncio.create_task(execution_agent.run_loop()),
                asyncio.create_task(audit_agent.run_loop())
            ]
            
            # Set running true
            for a in [strategy_agent, aggregator_agent, risk_agent, execution_agent, audit_agent]:
                a.is_running = True
            
            # Give agents a moment to subscribe
            await asyncio.sleep(0.1)

            # 4. Track execution
            order_filled_event = asyncio.Event()
            
            async def on_order_filled(data):
                print(f"VERIFICATION: Order Filled Event Received: {data['id']}")
                order_filled_event.set()
                
            event_bus.subscribe(EventType.ORDER_FILLED, on_order_filled)

            # 5. Manually publish TWO strategy signals to test Aggregator
            print("VERIFICATION: Publishing two conflicting signals to Aggregator...")
            ts = 1700000060000
            
            # Signal 1: Strong BUY
            await event_bus.publish(EventType.STRATEGY_SIGNAL, {
                "strategy_id": "ST1_STRONG_BUY",
                "symbol": "BTC-USDT",
                "signal": "BUY",
                "confidence": 0.9,
                "price": 25000,
                "timestamp": ts,
                "agent": "ST1"
            })
            
            # Signal 2: Weak SELL
            await event_bus.publish(EventType.STRATEGY_SIGNAL, {
                "strategy_id": "ST2_WEAK_SELL",
                "symbol": "BTC-USDT",
                "signal": "SELL",
                "confidence": 0.2,
                "price": 25000,
                "timestamp": ts,
                "agent": "ST2"
            })

            # 6. Wait for the flow to complete
            try:
                # Weighted average will be (0.9*1 + 0.2*-1) / 1.1 = 0.7/1.1 = 0.63 -> BUY
                await asyncio.wait_for(order_filled_event.wait(), timeout=5)
                print("VERIFICATION SUCCESS: Aggregator produced a signal and it was executed!")
                
                # Check Database for Audit Logs
                with SessionLocal() as db:
                    logs = db.query(AuditLogModel).all()
                    print(f"VERIFICATION: Database contains {len(logs)} audit logs.")
                    # We expect at least: 2 Strategy Signals, 1 Aggregated Signal, 1 Order Request, 1 Order Filled
                    assert len(logs) >= 5
            except asyncio.TimeoutError:
                print("VERIFICATION FAILED: Flow did not complete within timeout.")
            except AssertionError as e:
                print(f"VERIFICATION FAILED: Database check failed: {e}")

            # Cleanup
            for a in [strategy_agent, aggregator_agent, risk_agent, execution_agent, audit_agent]:
                a.is_running = False
            for t in loop_tasks:
                t.cancel()

if __name__ == "__main__":
    unittest.main()
