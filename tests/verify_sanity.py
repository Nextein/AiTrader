import asyncio
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.sanity_agent import SanityAgent
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifySanity")

async def main():
    print(f"Testing SanityAgent with model: {settings.OLLAMA_MODEL} at {settings.OLLAMA_BASE_URL}")
    agent = SanityAgent()
    
    test_symbols = [
        "BTC-USDT",
        "ETH-USDT",
        "LAVA-USDT",
        "SFP-USDT",
        "DEEP-USDT",
        "BTCUP-USDT",
        "1000PEPE-USDT",
        "LTC-USDT"
    ]
    
    print("\nStarting tests...")
    for symbol in test_symbols:
        try:
            is_valid = await agent.check_symbol(symbol)
            result_str = "PASSED (Valid)" if is_valid else "FAILED (Derivative/Weird)"
            print(f"Symbol: {symbol:15} -> {result_str}")
        except Exception as e:
            print(f"Symbol: {symbol:15} -> ERROR: {e}")
            
if __name__ == "__main__":
    asyncio.run(main())
