import asyncio
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings
import logging

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
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert cryptocurrency market analyst and blockchain scholar. 
Your task is to determine if a given trading symbol represents a 'Sanity' cryptocurrency (any legitimate native coin, project token, or meme coin) OR if it is a 'Derivative/Weird' asset (leveraged tokens, multi-asset indices, or specific derivative wrappers).

DEFINITION OF DERIVATIVE/WEIRD (REJECT - FALSE):
1. Leveraged tokens: Any symbol containing 'UP', 'DOWN', 'BULL', 'BEAR' (e.g., BTCUP, ETHDOWN).
2. Multiplier contracts: Any symbol starting with numbers like '1000', '500', etc. (e.g., 1000PEPE, 1000SHIB).
3. Composite indices: Any basket or index tokens (e.g., DEFI-INDEX).

DEFINITION OF SANITY (ACCEPT - TRUE):
1. Established Cryptos: BTC, ETH, SOL, XRP, etc.
2. Project Tokens & Niche/Small Coins: Regardless of popularity, if it's a standalone token (e.g., LAVA, SFP, DEEP, COW, ALT, JUP, etc.), it is VALID.
3. Standard Meme Coins: PEPE, DOGE, SHIB are VALID (only the '1000' multiplier versions are invalid).

CRITICAL INSTRUCTION:
If a symbol is NICHE or UNKNOWN to you, but it DOES NOT clearly follow the 'Derivative/Weird' patterns (UP/DOWN/1000x), you MUST return 'TRUE'. We want to trade all real tokens, even the tiny ones.

Response MUST be exactly 'TRUE' if it's a valid coin/token, or 'FALSE' if it's a derivative. 
Provide NO other text, explanations, or punctuation. Just return 'TRUE' or 'FALSE'."""),
            ("user", "Verify this symbol: {symbol}")
        ])
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
            logger.info(f"SanityAgent: Check for {symbol} ({base_symbol}) -> {is_valid} (Raw: '{result}')")
            self.processed_count += 1
            return is_valid
        except Exception as e:
            logger.error(f"SanityAgent: Error checking {symbol}: {e}")
            # Safe default: False
            return False
