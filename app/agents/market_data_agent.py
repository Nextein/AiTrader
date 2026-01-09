import asyncio
import ccxt.async_support as ccxt
import pandas as pd
from datetime import datetime
from app.agents.base_agent import BaseAgent
from app.core.config import settings
from app.core.event_bus import event_bus, EventType
from app.core.database import SessionLocal
from app.models.models import CandleModel
import logging

logger = logging.getLogger("MarketDataAgent")

class MarketDataAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="MarketDataAgent")
        self.exchange = ccxt.bingx({
            'apiKey': settings.BINGX_API_KEY,
            'secret': settings.BINGX_SECRET_KEY,
            'options': {
                'defaultType': 'swap',  # Trading perps
                'sandbox': settings.BINGX_IS_SANDBOX, 
            }
        })
        self.symbol = settings.TRADING_SYMBOL
        self.timeframe = settings.TIMEFRAME

    async def run_loop(self):
        while self.is_running:
            try:
                # Fetch OHLCV
                ohlcv = await self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=100)
                
                # Convert to DataFrame just to be sure it's clean and for potential enrichment
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Publish event
                # We publish the raw relevant data or the dataframe
                # For simplicity, sending the latest candle and the full history
                data = {
                    "symbol": self.symbol,
                    "timeframe": self.timeframe,
                    "candles": ohlcv,  # Raw list of lists
                    "latest_close": df['close'].iloc[-1],
                    "timestamp": df['timestamp'].iloc[-1],
                    "agent": self.name
                }
                
                await event_bus.publish(EventType.MARKET_DATA, data)

                # Persist to DB
                self.persist_candles(data["candles"])
                logger.info(f"[{self.symbol}] Fetched 100 candles. Latest Close: {data['latest_close']}")
                
            except Exception as e:
                logger.error(f"Error fetching data: {e}")
                await event_bus.publish(EventType.ERROR, {"agent": self.name, "error": str(e)})

            # Sleep for a bit (e.g., 60s for 1m candles, but let's check every 10s to be responsive)
            await asyncio.sleep(10)

    def persist_candles(self, candles):
        try:
            with SessionLocal() as db:
                for c in candles:
                    # c is [timestamp, open, high, low, close, volume]
                    ts = datetime.fromtimestamp(c[0] / 1000.0)
                    
                    # Check if already exists to avoid duplicates
                    # Optimization: In production use ON CONFLICT or a more efficient check
                    existing = db.query(CandleModel).filter(
                        CandleModel.symbol == self.symbol,
                        CandleModel.timestamp == ts,
                        CandleModel.timeframe == self.timeframe
                    ).first()
                    
                    if not existing:
                        candle = CandleModel(
                            symbol=self.symbol,
                            timeframe=self.timeframe,
                            timestamp=ts,
                            open=c[1],
                            high=c[2],
                            low=c[3],
                            close=c[4],
                            volume=c[5]
                        )
                        db.add(candle)
                db.commit()
                # Optional: log persistence success if needed, but might be too noisy
        except Exception as e:
             logger.error(f"Error persisting candles: {e}")

    async def stop(self):
        await super().stop()
        await self.exchange.close()
