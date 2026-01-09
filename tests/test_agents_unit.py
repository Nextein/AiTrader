import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
import pandas as pd
from app.agents.base_agent import BaseAgent
from app.agents.risk_agent import RiskAgent
from app.agents.governor_agent import GovernorAgent
from app.agents.market_data_agent import MarketDataAgent
from app.agents.execution_agent import ExecutionAgent
from app.agents.aggregator_agent import AggregatorAgent
from app.agents.strategy_agent import StrategyAgent
from app.agents.ema_cross_strategy_agent import EMACrossStrategyAgent
from app.agents.anomaly_detection_agent import AnomalyDetectionAgent
from app.core.event_bus import event_bus, EventType
from app.core.config import settings

class MockAgent(BaseAgent):
    async def run_loop(self):
        try:
            while self.is_running:
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            pass

class TestAgentsUnit(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Global mock for ccxt to prevent network calls
        self.patcher_ccxt = patch('ccxt.async_support.bingx', return_value=AsyncMock())
        self.mock_ccxt_global = self.patcher_ccxt.start()

    def tearDown(self):
        self.patcher_ccxt.stop()

    async def asyncSetUp(self):
        self.original_demo_mode = settings.DEMO_MODE
        # Reset event bus or other global state if necessary
        pass

    async def asyncTearDown(self):
        settings.DEMO_MODE = self.original_demo_mode
        event_bus.clear_subscribers()

    async def test_base_agent_status(self):
        agent = MockAgent(name="TestAgent")
        status = agent.get_status()
        self.assertEqual(status["name"], "TestAgent")
        self.assertFalse(status["is_running"])
        self.assertTrue(status["is_active"])
        
        # Start in a task so it doesn't block the test
        task = asyncio.create_task(agent.start())
        await asyncio.sleep(0.05) # Give it a moment to start
        status = agent.get_status()
        self.assertTrue(status["is_running"])
        self.assertGreaterEqual(status["uptime"], 0)
        
        await agent.stop()
        await asyncio.sleep(0.05)
        status = agent.get_status()
        self.assertFalse(status["is_running"])
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @patch('app.agents.risk_agent.ccxt.bingx')
    async def test_risk_agent_init_modes(self, mock_bingx):
        # Test Live Mode
        settings.DEMO_MODE = False
        risk_agent_live = RiskAgent()
        self.assertIsNotNone(risk_agent_live.exchange)
        mock_bingx.assert_called()

        # Test Demo Mode
        settings.DEMO_MODE = True
        risk_agent_demo = RiskAgent()
        from app.core.demo_engine import demo_engine
        self.assertEqual(risk_agent_demo.exchange, demo_engine)

    @patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock)
    async def test_risk_agent_signal_rejection(self, mock_publish):
        settings.DEMO_MODE = True
        agent = RiskAgent()
        agent.is_running = True
        
        # Test low confidence
        await agent.on_signal({"confidence": 0.5, "symbol": "BTC-USDT"})
        mock_publish.assert_not_called()

    @patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock)
    async def test_risk_agent_dynamic_sizing_atr(self, mock_publish):
        settings.DEMO_MODE = True
        from app.core.demo_engine import demo_engine
        demo_engine.fetch_balance = AsyncMock(return_value={'USDT': {'free': 10000.0}})
        
        agent = RiskAgent()
        agent.is_running = True
        
        # Mock ATR calculation
        # Candles: [timestamp, open, high, low, close, volume]
        candles = [[i, 50000, 51000, 49000, 50000, 100] for i in range(20)]
        agent.latest_candles = candles
        
        # Signal data
        signal_data = {
            "symbol": "BTC-USDT",
            "signal": "BUY",
            "confidence": 0.9,
            "price": 50000,
            "rationale": "Strong indicator"
        }
        
        await agent.on_signal(signal_data)
        
        # Verify order request was published
        mock_publish.assert_called()
        args, kwargs = mock_publish.call_args
        event_type, order_request = args
        self.assertEqual(event_type, EventType.ORDER_REQUEST)
        self.assertEqual(order_request["symbol"], "BTC-USDT")
        self.assertEqual(order_request["side"], "buy")
        self.assertIn("Dynamic Size", order_request["rationale"])

    async def test_risk_agent_balance_extraction(self):
        agent = RiskAgent()
        
        # Mock different balance formats
        formats = [
            ({'USDT': {'free': 100.0}}, 100.0),
            ({'free': {'USDT': 200.0}}, 200.0),
            ({'info': {'data': {'balance': '300.0'}}}, 300.0),
            ({'USDT': 400.0}, 400.0)
        ]
        
        for balance_input, expected in formats:
            agent.exchange.fetch_balance = AsyncMock(return_value=balance_input)
            agent.latest_candles = [[i, 50, 51, 49, 50, 10] for i in range(20)]
            agent.is_running = True
            
            with patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock) as mock_pub:
                await agent.on_signal({"confidence": 0.9, "symbol": "BTC-USDT", "signal": "BUY", "price": 50})
                self.assertTrue(mock_pub.called, f"Failed for format {balance_input}")

    @patch('app.agents.governor_agent.SessionLocal')
    @patch('ccxt.async_support.bingx', return_value=AsyncMock())
    async def test_governor_agent_init_and_stop(self, mock_ccxt, mock_session):
        gov = GovernorAgent()
        self.assertGreater(len(gov.agents), 0)
        
        # Mock agent tasks to avoid running full loops
        for agent in gov.agents:
            agent.start = AsyncMock()
            agent.stop = AsyncMock()
            
        await gov.start()
        self.assertTrue(gov.is_running)
        
        # Check if tasks are created (agents + equity snapshot)
        self.assertGreater(len(gov.tasks), 0)
        
        await gov.stop()
        self.assertFalse(gov.is_running)
        for agent in gov.agents:
            agent.stop.assert_called()

    @patch('app.agents.market_data_agent.SessionLocal')
    @patch('ccxt.async_support.bingx')
    async def test_market_data_agent_fetch_and_publish(self, mock_ccxt, mock_session):
        mock_exchange = AsyncMock()
        mock_ccxt.return_value = mock_exchange
        
        # Mock fetch_ohlcv
        ohlcv = [[123456789, 50000, 51000, 49000, 50500, 100]]
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=ohlcv)
        
        agent = MarketDataAgent()
        agent.is_running = True
        agent.is_active = True
        agent.symbols = ["BTC-USDT"]
        
        with patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock) as mock_pub:
            await agent.fetch_and_publish("BTC-USDT", "1m")
            
            mock_pub.assert_called()
            args, _ = mock_pub.call_args
            event_type, data = args
            self.assertEqual(event_type, EventType.MARKET_DATA)
            self.assertEqual(data["symbol"], "BTC-USDT")
            self.assertEqual(data["latest_close"], 50500)

    def test_market_data_agent_timeframe_to_minutes(self):
        agent = MarketDataAgent()
        self.assertEqual(agent._timeframe_to_minutes("1m"), 1)
        self.assertEqual(agent._timeframe_to_minutes("1h"), 60)
        self.assertEqual(agent._timeframe_to_minutes("1d"), 1440)
        self.assertEqual(agent._timeframe_to_minutes("invalid"), 60)

    @patch('ccxt.async_support.bingx', return_value=AsyncMock())
    async def test_execution_agent_order(self, mock_ccxt):
        settings.DEMO_MODE = True
        agent = ExecutionAgent()
        agent.is_running = True
        agent.latest_prices["BTC-USDT"] = 50000.0
        
        # Mock exchange create_order
        agent.exchange.create_order = AsyncMock(return_value={'id': 'test-id', 'status': 'filled'})
        
        with patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock) as mock_pub:
            await agent.on_order_request({"symbol": "BTC-USDT", "side": "buy", "amount": 0.1})
            
            agent.exchange.create_order.assert_called()
            mock_pub.assert_called_with(EventType.ORDER_FILLED, unittest.mock.ANY)

    @patch('ccxt.async_support.bingx', return_value=AsyncMock())
    async def test_execution_agent_emergency_exit(self, mock_ccxt):
        agent = ExecutionAgent()
        agent.exchange.cancel_all_orders = AsyncMock()
        agent.exchange.fetch_balance = AsyncMock(return_value={'USDT': {'free': 100}})
        agent.exchange.fetch_positions = AsyncMock(return_value=[
            {'symbol': 'BTC-USDT', 'contracts': '0.1'} # Long position
        ])
        agent.exchange.create_order = AsyncMock()
        
        await agent.on_emergency_exit({})
        
        agent.exchange.cancel_all_orders.assert_called()
        agent.exchange.fetch_positions.assert_called()
        # Should create a sell order to close long
        agent.exchange.create_order.assert_called_with(
            symbol='BTC-USDT', type='market', side='sell', amount=0.1, params={'reduceOnly': True}
        )

    async def test_aggregator_agent_voting(self):
        agent = AggregatorAgent(window_seconds=0.01)
        agent.is_running = True
        agent.current_regime = "TRENDING"
        
        # Signal 1: EMA strategy (multiplier 1.5 in TRENDING)
        s1 = {"strategy_id": "EMA_Cross", "symbol": "BTC-USDT", "signal": "BUY", "confidence": 0.8, "price": 50000, "timestamp": 1000}
        # Signal 2: RSI strategy (multiplier 0.5 in TRENDING)
        s2 = {"strategy_id": "RSI_MACD", "symbol": "BTC-USDT", "signal": "SELL", "confidence": 0.6, "price": 50000, "timestamp": 1000}
        
        with patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock) as mock_pub:
            # We must await on_strategy_signal which starts the task
            await agent.on_strategy_signal(s1)
            await agent.on_strategy_signal(s2)
            
            # Wait for delayed_process to finish (more than 0.01s)
            # and ensure all tasks are done
            for _ in range(10):
                if not agent.processing_tasks:
                    break
                await asyncio.sleep(0.02)
            
            mock_pub.assert_called()
            args, _ = mock_pub.call_args
            event_type, data = args
            self.assertEqual(event_type, EventType.SIGNAL)
            self.assertEqual(data["signal"], "BUY")
            self.assertAlmostEqual(data["confidence"], 0.6)

    @patch('pandas_ta.ema')
    async def test_ema_cross_strategy(self, mock_ema):
        agent = EMACrossStrategyAgent(fast_period=5, slow_period=10)
        agent.is_running = True
        
        # Mock EMA values to trigger a cross
        # return_value is a Series. We need two calls (fast and slow)
        # Fast EMA: [..., 50, 60]
        # Slow EMA: [..., 50, 55]
        # Prev: 50 <= 50 (True), Now: 60 > 55 (True) -> CROSS!
        mock_ema.side_effect = [
            pd.Series([50] * 14 + [60]), # Fast
            pd.Series([50] * 14 + [55])  # Slow
        ]
        
        candles = [[i, 50, 51, 49, 50, 10] for i in range(15)]
        
        with patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock) as mock_pub:
            await agent.on_market_data({"symbol": "BTC-USDT", "timeframe": "1m", "candles": candles, "timestamp": 123456789})
            
            mock_pub.assert_called()
            args, _ = mock_pub.call_args
            event_type, data = args
            self.assertEqual(event_type, EventType.STRATEGY_SIGNAL)
            self.assertEqual(data["signal"], "BUY")

    async def test_anomaly_detection_agent(self):
        agent = AnomalyDetectionAgent()
        agent.is_running = True
        
        # Test extreme price drop (flash crash)
        # candles: [timestamp, open, high, low, close, volume]
        prev_candles = [[i, 50000, 50000, 50000, 50000, 10] for i in range(10)]
        crash_candle = [10, 50000, 50000, 10000, 10000, 100]
        
        with patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock) as mock_pub:
            await agent.on_market_data({
                "symbol": "BTC-USDT", 
                "candles": prev_candles + [crash_candle],
                "latest_close": 10000
            })
            
            # Should trigger an alert
            mock_pub.assert_called()

    @patch('app.agents.audit_log_agent.SessionLocal')
    async def test_audit_log_agent(self, mock_session):
        from app.agents.audit_log_agent import AuditLogAgent
        agent = AuditLogAgent()
        agent.is_running = True
        
        mock_db = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_db
        
        callback = agent.handle_event(EventType.ORDER_FILLED)
        await callback({"id": "test", "agent": "ExecutionAgent"})
        
        mock_db.add.assert_called()
        mock_db.commit.assert_called()

    async def test_rsi_macd_strategy(self):
        agent = StrategyAgent(strategy_id="RSI_MACD")
        agent.is_running = True
        
        # We'll use a mock to bypass the pandas_ta append problem
        # by patching the indicators directly where they are read from df
        with patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock) as mock_pub:
            # We mock the indicators extraction
            with patch('pandas.DataFrame.__getitem__') as mock_getitem:
                # Return a mock Series that behaves like the indicators
                mock_rsi = MagicMock()
                mock_rsi.iloc.__getitem__.return_value = 20.0 # RSI < 35
                
                mock_macd = MagicMock()
                mock_macd.iloc.__getitem__.side_effect = [1.0, 0.0] # MACD > MACD_Signal
                
                def getitem_side_effect(key):
                    if key == 'RSI_14': return mock_rsi
                    if key == 'MACD_12_26_9': return mock_macd
                    if key == 'MACDs_12_26_9': return mock_macd
                    return MagicMock() # Fallback
                
                mock_getitem.side_effect = getitem_side_effect
                
                # Mock columns to avoid "Indicators not yet available"
                with patch('pandas.DataFrame.columns', new_callable=PropertyMock) as mock_cols:
                    mock_cols.return_value = pd.Index(['RSI_14', 'MACD_12_26_9', 'MACDs_12_26_9'])
                    
                    candles = [[i, 50, 50, 50, 50, 10] for i in range(40)]
                    await agent.on_market_data({"symbol": "BTC-USDT", "candles": candles, "timestamp": 1234, "latest_close": 50})
                    
                    mock_pub.assert_called()

    async def test_regime_detection_agent(self):
        from app.agents.regime_detection_agent import RegimeDetectionAgent
        agent = RegimeDetectionAgent()
        agent.is_running = True
        
        # TRENDING: adx > 25. Strong steady trend.
        prices = [100 + i*5 for i in range(50)]
        candles = [[i, p, p+2, p-2, p, 10] for i, p in enumerate(prices)]
        
        with patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock) as mock_pub:
            await agent.on_market_data({"symbol": "BTC-USDT", "candles": candles, "timestamp": 123456789})
            
            self.assertEqual(agent.current_regime, "TRENDING")
            mock_pub.assert_called_with(EventType.REGIME_CHANGE, unittest.mock.ANY)

    @patch('app.core.event_bus.event_bus.publish', new_callable=AsyncMock)
    async def test_anomaly_detection_spam(self, mock_pub):
        from app.agents.anomaly_detection_agent import AnomalyDetectionAgent
        agent = AnomalyDetectionAgent()
        agent.is_running = True
        agent.max_signals_per_minute = 2 # Low for testing
        
        # Mock loop time
        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.time.side_effect = [1, 2, 3, 4] # Timestamps
            
            # Send 3 signals
            await agent.on_signal({"symbol": "BTC-USDT"})
            await agent.on_signal({"symbol": "ETH-USDT"})
            await agent.on_signal({"symbol": "SOL-USDT"}) # This should trigger anomaly
            
            mock_pub.assert_called_with(EventType.ANOMALY_ALERT, unittest.mock.ANY)

if __name__ == "__main__":
    unittest.main()
