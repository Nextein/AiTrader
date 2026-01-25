import asyncio
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
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
        self.chain = self.prompt | self.llm | StrOutputParser()

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
            
            response = await self.chain.ainvoke({"symbol": base_symbol})
            result = response.strip().upper()
            
            # Being robust with the response
            is_valid = "TRUE" in result and "FALSE" not in result
            self.log_llm_call("symbol_verify", symbol, {"is_valid": is_valid, "raw": result})
            self.processed_count += 1
            return is_valid
        except Exception as e:
            self.log(f"Error checking {symbol}: {e}", level="ERROR")
            # Safe default: False
            return False
