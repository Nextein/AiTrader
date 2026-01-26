import asyncio
from typing import List
from app.agents.base_agent import BaseAgent
from app.agents.market_data_agent import MarketDataAgent
from app.agents.value_areas_agent import ValueAreasAgent
from app.agents.market_structure_agent import MarketStructureAgent
from app.agents.strategy_agent import StrategyAgent
from app.agents.risk_agent import RiskAgent
from app.agents.execution_agent import ExecutionAgent
from app.agents.audit_log_agent import AuditLogAgent
from app.agents.ema_strategy_agent import EMAStrategyAgent
from app.agents.cycles_strategy_agent import CyclesStrategyAgent
from app.agents.bounce_strategy_agent import BounceStrategyAgent
from app.agents.support_resistance_agent import SupportResistanceAgent
from app.agents.fibonacci_agent import FibonacciAgent
from app.agents.anchored_vwap_agent import AnchoredVWAPAgent
from app.agents.sfp_strategy_agent import SFPStrategyAgent
from app.agents.analyst_agent import AnalystAgent
from app.agents.trader_agent import TraderAgent
from app.agents.aggregator_agent import AggregatorAgent
from app.agents.regime_detection_agent import RegimeDetectionAgent
from app.agents.anomaly_detection_agent import AnomalyDetectionAgent
from app.agents.dummy_strategy_agent import DummyStrategyAgent
from app.agents.sanity_agent import SanityAgent
from app.core.event_bus import event_bus, EventType
from app.core.database import SessionLocal
from app.models.models import EquityModel
from app.core.config import settings
import ccxt.async_support as ccxt
import logging
import random


logger = logging.getLogger("Governor")

class GovernorAgent:
    def __init__(self):
        self.sanity_agent = SanityAgent()
        self.agents: List[BaseAgent] = [
            MarketDataAgent(),
            ValueAreasAgent(),
            MarketStructureAgent(),
            self.sanity_agent,
            RegimeDetectionAgent(),
            EMAStrategyAgent(),
            CyclesStrategyAgent(),
            BounceStrategyAgent(),
            SupportResistanceAgent(),
            FibonacciAgent(),
            AnchoredVWAPAgent(),
            SFPStrategyAgent(),
            AnalystAgent(),
            TraderAgent(),
            AggregatorAgent(),
            RiskAgent(),
            ExecutionAgent(),
            AuditLogAgent(),
            AnomalyDetectionAgent(),
            # DummyStrategyAgent(signal_interval=5, name="DummyStrategy1")
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
            
        # 3. Initialize Demo Balance if needed
        if settings.DEMO_MODE:
            from app.core.demo_engine import demo_engine
            await demo_engine.initialize_balance()
            
        # 4. Start equity snapshotting
        self.tasks.append(asyncio.create_task(self.equity_snapshot_loop()))
            
        # 4. Start symbol initialization
        self.tasks.append(asyncio.create_task(self.initialize_symbols_task()))

        logger.info("Governor: All agents are running.")

    async def equity_snapshot_loop(self):
        """Periodically snapshots the account equity for history."""
        # Use an exchange instance for balance fetching
        if settings.DEMO_MODE:
            from app.core.demo_engine import demo_engine
            exchange = demo_engine
        else:
            exchange = ccxt.bingx({
                'apiKey': settings.BINGX_API_KEY,
                'secret': settings.BINGX_SECRET_KEY,
                'options': {
                    'defaultType': 'swap',
                    'sandbox': settings.BINGX_IS_SANDBOX,
                }
            })
        
        try:
            while self.is_running:
                try:
                    logger.debug(f"GovernorAgent: Fetching balance for equity snapshot (Demo: {settings.DEMO_MODE})")
                    balance = await exchange.fetch_balance()
                    
                    total_equity = 0.0
                    try:
                        if settings.DEMO_MODE:
                            total_equity = float(balance['total']['USDT'])
                        else:
                            # Try multiple possible keys for total equity in CCXT/BingX response
                            if 'total' in balance and 'USDT' in balance['total']:
                                total_equity = float(balance['total']['USDT'])
                            elif 'USDT' in balance and isinstance(balance['USDT'], dict) and 'total' in balance['USDT']:
                                total_equity = float(balance['USDT']['total'])
                            elif 'info' in balance and 'data' in balance['info'] and 'balance' in balance['info']['data']:
                                total_equity = float(balance['info']['data']['balance'])
                            elif 'total' in balance and isinstance(balance['total'], (int, float)):
                                total_equity = float(balance['total'])
                            else:
                                # Final fallback
                                total_equity = float(balance.get('USDT', {}).get('total', 0)) or float(balance.get('USDT', 0))
                    except (KeyError, TypeError, ValueError) as e:
                        logger.warning(f"GovernorAgent: Extraction failed for {balance}. Error: {e}")
                        # If extraction failed but we have some number in the response, try to find it
                        if isinstance(balance, dict):
                            # Try to find anything that looks like a balance
                            if 'USDT' in balance:
                                if isinstance(balance['USDT'], (int, float)): total_equity = float(balance['USDT'])
                                elif isinstance(balance['USDT'], dict): total_equity = float(balance['USDT'].get('total', balance['USDT'].get('free', 0)))
                            elif 'free' in balance and 'USDT' in balance['free']:
                                total_equity = float(balance['free']['USDT'])
                    
                    if not total_equity:
                        logger.warning(f"GovernorAgent: Could not determine equity value from {balance}")
                        total_equity = 0.0

                    logger.debug(f"GovernorAgent: Processed equity value: {total_equity}")

                    with SessionLocal() as db:
                        equity_entry = EquityModel(total_equity=total_equity)
                        db.add(equity_entry)
                        db.commit()
                    
                    logger.info(f"Equity Snapshot Saved: {total_equity:.2f} USDT")
                except Exception as e:
                    logger.error(f"Error in equity snapshot: {e}")
                
                # Snapshot every hour in production, but more frequent for demo/mvp visibility
                sleep_time = 3600 if not settings.BINGX_IS_SANDBOX else 60 
                await asyncio.sleep(sleep_time)
        finally:
            await exchange.close()

    async def initialize_symbols_task(self):
        """Fetches, filters, prioritizes, and sanitizes symbols."""
        logger.info("Governor: Starting symbol initialization...")
        
        # Use a temporary exchange instance to fetch markets
        exchange = ccxt.bingx({
            'apiKey': settings.BINGX_API_KEY,
            'secret': settings.BINGX_SECRET_KEY,
            'options': {
                'defaultType': 'swap',
                'sandbox': settings.BINGX_IS_SANDBOX,
            }
        })
        
        try:
            markets = await exchange.load_markets()
            
            # Filter for USDT perpetual contracts
            all_symbols = []
            for symbol, market in markets.items():
                # BingX/CCXT linear and quote criteria
                if market.get('linear') and market.get('quote') == 'USDT':
                    all_symbols.append(symbol)
                elif '-USDT' in symbol and market.get('type') == 'swap':
                    all_symbols.append(symbol)

            if not all_symbols:
                 # Fallback
                 all_symbols = [s for s in markets.keys() if '-USDT' in s]

            logger.info(f"Governor: Found {len(all_symbols)} potential USDT perpetual symbols.")

            # Prioritization: Initial List (from settings or just first few)
            trading_symbols = settings.TRADING_SYMBOLS if hasattr(settings, 'TRADING_SYMBOLS') else []
            initial_pool = [s for s in trading_symbols if s in all_symbols]
            
            # If TRADING_SYMBOLS has less than MAX_SYMBOLS, fill with others (prefer common ones if possible)
            if len(initial_pool) < settings.MAX_SYMBOLS:
                others = [s for s in all_symbols if s not in initial_pool]
                # In a real app we might sort by volume. Here we'll just take the next few.
                initial_pool.extend(others[:settings.MAX_SYMBOLS-len(initial_pool)])
            
            remaining = [s for s in all_symbols if s not in initial_pool]
            random.shuffle(remaining)
            
            prioritized_list = initial_pool + remaining
            
            logger.info(f"Governor: Starting sanity checks on {len(prioritized_list)} symbols. Limit: {settings.MAX_SYMBOLS}")
            
            approved_count = 0
            for symbol in prioritized_list:
                if not self.is_running or approved_count >= settings.MAX_SYMBOLS:
                    break
                
                # Check with Sanity Agent
                is_sane = await self.sanity_agent.check_symbol(symbol)
                
                if is_sane:
                    logger.info(f"Governor: Symbol {symbol} PASSED sanity check ({approved_count + 1}/{settings.MAX_SYMBOLS}).")
                    # Broadcast approval
                    # We use a small delay between publishing to let agents process
                    await event_bus.publish(EventType.SYMBOL_APPROVED, {"symbol": symbol})
                    approved_count += 1
                else:
                    logger.warning(f"Governor: Symbol {symbol} FAILED sanity check (Derivative/Weird). Skipping.")
                
                # Throttle LLM requests
                await asyncio.sleep(0.5)

            if approved_count >= settings.MAX_SYMBOLS:
                logger.info(f"Governor: Reached MAX_SYMBOLS limit ({settings.MAX_SYMBOLS}). Stopping initialization.")

        except Exception as e:
            logger.error(f"Governor: Error during symbol initialization: {e}", exc_info=True)
        finally:
            await exchange.close()
            logger.info("Governor: Symbol initialization task finished.")

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

    async def emergency_stop(self):
        logger.warning("Governor: EMERGENCY STOP TRIGGERED!")
        self.is_running = False
        
        # 1. Publish Emergency Exit Event (Execution agent will close positions)
        await event_bus.publish(EventType.EMERGENCY_EXIT, {"reason": "User manual trigger"})
        
        # 2. Stop all agents
        for agent in self.agents:
            await agent.stop()
            
        # 3. Cancel tasks
        for task in self.tasks:
            task.cancel()
        
        self.tasks = []
        logger.warning("Governor: System emergency stop complete.")

# Global instance
governor = GovernorAgent()
