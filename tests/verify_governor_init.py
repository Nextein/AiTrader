import asyncio
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.governor_agent import GovernorAgent
from app.core.event_bus import event_bus, EventType
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyGovernor")

async def main():
    print("Testing GovernorAgent symbol discovery and sanity integration...")
    
    # Mock MarketDataAgent to avoid full start if possible, 
    # but GovernorAgent creates them in __init__.
    governor = GovernorAgent()
    
    # Track approved symbols via event bus
    approved_symbols = []
    
    async def on_symbol_approved(data):
        symbol = data["symbol"]
        approved_symbols.append(symbol)
        print(f"EVENT: Symbol approved -> {symbol}")

    event_bus.subscribe(EventType.SYMBOL_APPROVED, on_symbol_approved)
    
    # Start the initialization task (we don't start the full governor to avoid background loops)
    # But we need sanity_agent to be "running" if it has a loop (it does, but it's not strictly needed for check_symbol)
    governor.is_running = True
    
    # We'll only run the initialize_symbols_task for a bit or until some results come in
    print("Running initialize_symbols_task...")
    task = asyncio.create_task(governor.initialize_symbols_task())
    
    # Wait for a few approvals or a timeout
    try:
        await asyncio.wait_for(task, timeout=60) # 60s for a few checks
    except asyncio.TimeoutError:
        print("Test timed out (intended after some checks)")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        governor.is_running = False
        if not task.done():
            task.cancel()
    
    print(f"\nTotal symbols approved during test: {len(approved_symbols)}")
    print(f"First 5 approved: {approved_symbols[:5]}")

if __name__ == "__main__":
    asyncio.run(main())
