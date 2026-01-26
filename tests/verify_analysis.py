import asyncio
import logging
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.market_data_agent import MarketDataAgent
from app.agents.market_structure_agent import MarketStructureAgent
from app.core.analysis import AnalysisManager
from app.core.config import settings
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verification")

async def verify():
    # Force some settings for testing
    settings.TRADING_SYMBOLS = ["BTC-USDT"]
    settings.TIMEFRAMES = ["4h", "1h"]
    
    logger.info("Starting MarketDataAgent and MarketStructureAgent...")
    
    md_agent = MarketDataAgent()
    ms_agent = MarketStructureAgent()
    
    # Start agents in background tasks
    ms_task = asyncio.create_task(ms_agent.start())
    await asyncio.sleep(1) # Give it a second to subscribe
    md_task = asyncio.create_task(md_agent.start())
    
    logger.info("Waiting for data processing (30s)...")
    await asyncio.sleep(30)
    
    logger.info("Checking Analysis Object for BTC-USDT...")
    analysis = await AnalysisManager.get_analysis("BTC-USDT")
    data = await analysis.get_data()
    
    # Clean up data for printing (remove big dataframes)
    print_data = data.copy()
    md_section = print_data.get("market_data", {})
    for tf in md_section:
        if isinstance(md_section[tf], pd.DataFrame):
            md_section[tf] = f"DataFrame (shape: {md_section[tf].shape})"
    
    logger.info("Analysis Object State (Structure):")
    # Only print structure part for brevity
    print(json.dumps(print_data.get("market_structure"), indent=2, default=str))
    
    # Verify specific fields
    ms = data.get("market_structure", {})
    success = True
    for tf in ["4h", "1h"]:
        if ms.get(tf) and ms[tf].get("last_updated"):
            logger.info(f"SUCCESS: Market structure for {tf} updated.")
        else:
            logger.warning(f"FAILURE: Market structure for {tf} NOT updated.")
            success = False

    # Stop agents
    await md_agent.stop()
    await ms_agent.stop()
    md_task.cancel()
    ms_task.cancel()
    logger.info("Verification complete.")
    return success

if __name__ == "__main__":
    asyncio.run(verify())
