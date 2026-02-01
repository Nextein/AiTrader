import asyncio
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from app.core.config import settings
from app.core.validation import validate_llm_response
import logging

from app.core.prompt_loader import PromptLoader

logger = logging.getLogger("SanityAgent")

class SanityAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="SanityAgent")
        # Ollama provides an OpenAI-compatible /v1 endpoint
        self.llm = ChatOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",  # Required but ignored by Ollama
            model=settings.OLLAMA_MODEL,
            temperature=0
        )
        self.prompt = PromptLoader.load("sanity", "symbol_verify")
        self.chain = self.prompt | self.llm | JsonOutputParser()

    async def run_loop(self):
        # SanityAgent is primarily a helper called by GovernorAgent, 
        # so it doesn't need its own loop for now.
        while self.is_running:
            await asyncio.sleep(1)

    async def check_symbol(self, symbol: str) -> bool:
        """
        Calls the LLM to verify if the symbol is a valid crypto coin/token.
        """
        try:
            # Clean symbol (e.g., BTC-USDT or BTC/USDT:USDT -> BTC)
            base_symbol = symbol.split('-')[0].split('/')[0].split(':')[0]
            
            response = await self.call_llm_with_retry(self.chain, {"symbol": base_symbol}, required_keys=["is_sanity"])
            
            if response:
                is_valid = response.get("is_sanity", False)
                await self.log_llm_call("symbol_verify", symbol, {"is_valid": is_valid, "response": response})
                self.processed_count += 1
                return is_valid
            else:
                return False
        except Exception as e:
            self.log(f"Error checking {symbol}: {e}", level="ERROR")
            # Safe default: False
            return False
