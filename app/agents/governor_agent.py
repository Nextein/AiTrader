import asyncio
from typing import List
from app.agents.base_agent import BaseAgent
from app.agents.market_data_agent import MarketDataAgent
from app.agents.strategy_agent import StrategyAgent
from app.agents.risk_agent import RiskAgent
from app.agents.execution_agent import ExecutionAgent
from app.agents.audit_log_agent import AuditLogAgent
from app.agents.ema_cross_strategy_agent import EMACrossStrategyAgent
from app.agents.aggregator_agent import AggregatorAgent
from app.agents.regime_detection_agent import RegimeDetectionAgent
from app.agents.anomaly_detection_agent import AnomalyDetectionAgent
from app.core.event_bus import event_bus, EventType
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Governor")

class GovernorAgent:
    def __init__(self):
        self.agents: List[BaseAgent] = [
            MarketDataAgent(),
            RegimeDetectionAgent(),
            StrategyAgent(strategy_id="RSI_MACD"),
            EMACrossStrategyAgent(fast_period=9, slow_period=21),
            AggregatorAgent(),
            RiskAgent(),
            ExecutionAgent(),
            AuditLogAgent(),
            AnomalyDetectionAgent()
        ]
        self.is_running = False
        self.tasks = []

    async def start(self):
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("Governor: Starting all agents...")
        
        # In a real hierarchical system, we might start them in order, 
        # but with the event bus, order doesn't strictly matter for initialization.
        for agent in self.agents:
            self.tasks.append(asyncio.create_task(agent.start()))
            
        logger.info("Governor: All agents are running.")

    async def stop(self):
        if not self.is_running:
            return
        
        logger.info("Governor: Stopping all agents...")
        for agent in self.agents:
            await agent.stop()
            
        # Cancel tasks
        for task in self.tasks:
            task.cancel()
        
        self.tasks = []
        self.is_running = False
        logger.info("Governor: System stopped.")

# Global instance
governor = GovernorAgent()
