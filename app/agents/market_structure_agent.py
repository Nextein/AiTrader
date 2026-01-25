import asyncio
import pandas as pd
import numpy as np
import time
import logging
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.core.event_bus import event_bus, EventType
from app.core.analysis import AnalysisManager
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from app.core.config import settings

logger = logging.getLogger("MarketStructureAgent")

class MarketStructureAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="MarketStructureAgent")
        self.processed_count = 0
        self.llm = ChatOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",
            model=settings.OLLAMA_MODEL,
            temperature=0
        )
        self.ema_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a technical analysis expert. Analyze the following EMA values and determine the market structure.
            
            EMAs provided: 9, 21, 55, 144, 252.
            
            Determine:
            1. 'emas_in_order':
               - 'ASCENDING' if 9 > 21 > 55 > 144 > 252 (Bullish stack)
               - 'DESCENDING' if 9 < 21 < 55 < 144 < 252 (Bearish stack)
               - 'NEUTRAL' otherwise.
            
            2. 'emas_fanning':
               - 'EXPANDING' if the EMAs are spreading apart compared to the previous values (distances between consecutive EMAs are increasing).
               - 'NEUTRAL' if they are not expanding (e.g., getting closer/contracting or staying same).

            Return your answer in JSON format with keys: "emas_in_order" and "emas_fanning".
            Values for emas_in_order MUST be one of: ASCENDING, DESCENDING, NEUTRAL.
            Values for emas_fanning MUST be one of: EXPANDING, NEUTRAL.
            """),
            ("user", "Current EMAs: {current_emas}\nPrevious EMAs: {previous_emas}")
        ])
        self.ema_chain = self.ema_prompt | self.llm | JsonOutputParser()

    async def run_loop(self):
        """Subscribe to market data updates and react"""
        event_bus.subscribe(EventType.MARKET_DATA, self.handle_market_data)
        
        # Keep alive - base class run_loop is abstract, but we just need to wait here
        # as we are event-driven
        while self.is_running:
            await asyncio.sleep(1)

    async def handle_market_data(self, data: Dict[str, Any]):
        """React to market data updates for a symbol + timeframe"""
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        logger.info(f"Received market data event for {symbol} {timeframe}")
        
        if not symbol or not timeframe:
            return

        try:
            # 1. Access Analysis Object
            analysis = await AnalysisManager.get_analysis(symbol)
            analysis_data = await analysis.get_data()
            
            # 2. Get DataFrame from market_data
            df = analysis_data.get("market_data", {}).get(timeframe)
            
            if df is None:
                logger.warning(f"DataFrame for {symbol} {timeframe} is None in AnalysisObject")
                return
            
            if not isinstance(df, pd.DataFrame):
                logger.warning(f"Data for {symbol} {timeframe} is not a DataFrame: {type(df)}")
                return

            if len(df) < 2:
                logger.warning(f"Insufficient data in DataFrame for {symbol} {timeframe}: {len(df)} rows")
                return

            # 3. Calculate Market Structure fields
            # We compare the last two confirmed candles (or latest vs prev)
            # Latest candle is usually index -1, previous is -2
            curr = df.iloc[-1]
            prev = df.iloc[-2]

            # Highs/Lows
            highs_state = "HIGHER" if curr['High'] > prev['High'] else ("LOWER" if curr['High'] < prev['High'] else "NEUTRAL")
            lows_state = "HIGHER" if curr['Low'] > prev['Low'] else ("LOWER" if curr['Low'] < prev['Low'] else "NEUTRAL")

            # Pivot Points
            curr_pivot = curr.get('Pivot Points')
            prev_pivot = prev.get('Pivot Points')
            pivot_state = "NEUTRAL"
            if curr_pivot is not None and prev_pivot is not None:
                pivot_state = "UP" if curr_pivot > prev_pivot else ("DOWN" if curr_pivot < prev_pivot else "NEUTRAL")

            # EMAs analysis via LLM
            ema_cols = [
                'Exponential Moving Average 9',
                'Exponential Moving Average 21',
                'Exponential Moving Average 55',
                'Exponential Moving Average 144',
                'Exponential Moving Average 252'
            ]
            
            curr_emas = {col: curr[col] for col in ema_cols if col in df.columns}
            prev_emas = {col: prev[col] for col in ema_cols if col in df.columns}
            
            emas_in_order = "NEUTRAL"
            emas_fanning = "NEUTRAL"
            
            if len(curr_emas) == 5 and not any(pd.isna(v) for v in curr_emas.values()):
                try:
                    res = await self.ema_chain.ainvoke({
                        "current_emas": curr_emas,
                        "previous_emas": prev_emas
                    })
                    emas_in_order = res.get("emas_in_order", "NEUTRAL").upper()
                    emas_fanning = res.get("emas_fanning", "NEUTRAL").upper()
                    
                    # Validation
                    if emas_in_order not in ["ASCENDING", "DESCENDING", "NEUTRAL"]:
                        emas_in_order = "NEUTRAL"
                    if emas_fanning not in ["EXPANDING", "NEUTRAL"]:
                        emas_fanning = "NEUTRAL"
                except Exception as e:
                    logger.error(f"LLM Error in MarketStructureAgent for {symbol}: {e}")

            # ADX State
            latest_adx = curr.get('Average Directional Index')
            adx_state = "NEUTRAL"
            if latest_adx is not None:
                adx_state = "TRENDING" if latest_adx >= 23 else "NEUTRAL"

            # 4. Update Analysis Object
            updates = {
                "highs": highs_state,
                "lows": lows_state,
                "pivot_points": pivot_state,
                "emas_in_order": emas_in_order,
                "emas_fanning": emas_fanning,
                "adx": adx_state,
                "last_updated": int(time.time())
            }
            
            await analysis.update_section("market_structure", updates, timeframe)
            
            # 5. Publish Analysis Update Event (Task 1)
            await event_bus.publish(EventType.ANALYSIS_UPDATE, {
                "symbol": symbol,
                "timeframe": timeframe,
                "section": "market_structure",
                "agent": self.name,
                "timestamp": int(time.time())
            })

            self.processed_count += 1
            logger.info(f"Updated market structure for {symbol} {timeframe}")

        except Exception as e:
            logger.error(f"Error in MarketStructureAgent for {symbol} {timeframe}: {e}", exc_info=True)
