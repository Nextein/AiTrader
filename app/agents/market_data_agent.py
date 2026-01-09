import asyncio
import ccxt.async_support as ccxt
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
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
        # Task 4: Fetch all symbols or use configured ones
        self.symbols = settings.TRADING_SYMBOLS if hasattr(settings, 'TRADING_SYMBOLS') else []
        self.fetch_all_symbols = getattr(settings, 'FETCH_ALL_SYMBOLS', False)
        
        # Task 6: Prioritized timeframes (higher to lower)
        self.timeframes = getattr(settings, 'TIMEFRAMES', [settings.TIMEFRAME]) if hasattr(settings, 'TIMEFRAMES') else [settings.TIMEFRAME]
        self.timeframe = settings.TIMEFRAME  # Default timeframe
        
        # Task 5: Cache tracking
        self.cache_enabled = True

    async def initialize_symbols(self):
        """Task 4: Fetch all available symbols from exchange"""
        if self.fetch_all_symbols:
            try:
                markets = await self.exchange.load_markets()
                # Filter for USDT perpetual contracts
                self.symbols = [symbol for symbol in markets.keys() if '/USDT' in symbol and ':USDT' in symbol]
                logger.info(f"Loaded {len(self.symbols)} symbols from exchange")
            except Exception as e:
                logger.error(f"Failed to load symbols: {e}. Using configured symbols.")
                self.symbols = settings.TRADING_SYMBOLS

    def get_status(self):
        status = super().get_status()
        status["config"] = {
            "symbols": self.symbols[:5] if len(self.symbols) > 5 else self.symbols,  # Show first 5
            "total_symbols": len(self.symbols),
            "timeframes": self.timeframes,
            "cache_enabled": self.cache_enabled
        }
        return status

    async def run_loop(self):
        """Main loop with prioritized fetching"""
        # Initialize symbols if needed
        if self.fetch_all_symbols or not self.symbols:
            await self.initialize_symbols()
        
        # Subscribe to market data requests
        event_bus.subscribe(EventType.MARKET_DATA_REQUEST, self.handle_data_request)
        
        while self.is_running and self.is_active:
            # Task 6: Fetch in order from higher timeframe to lower
            for timeframe in sorted(self.timeframes, key=lambda x: self._timeframe_to_minutes(x), reverse=True):
                if not self.is_running or not self.is_active:
                    break
                    
                for symbol in self.symbols:
                    if not self.is_running or not self.is_active:
                        break
                    try:
                        await self.fetch_and_publish(symbol, timeframe)
                    except Exception as e:
                        logger.error(f"Error fetching {symbol} {timeframe}: {e}")
                        await asyncio.sleep(0.1)  # Brief pause on error
            
            # Sleep between cycles
            await asyncio.sleep(10)

    async def fetch_and_publish(self, symbol: str, timeframe: str):
        """Fetch data with caching support (Task 5)"""
        # Check cache first
        if self.cache_enabled:
            cached_data = self.get_cached_data(symbol, timeframe)
            if cached_data and self.is_cache_valid(cached_data, timeframe):
                # Use cached data
                data = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "candles": cached_data,
                    "latest_close": cached_data[-1][4],
                    "timestamp": cached_data[-1][0],
                    "agent": self.name,
                    "from_cache": True
                }
                await event_bus.publish(EventType.MARKET_DATA, data)
                self.processed_count += 1
                return
        
        # Fetch fresh data
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            
            if not ohlcv:
                return
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            data = {
                "symbol": symbol,
                "timeframe": timeframe,
                "candles": ohlcv,
                "latest_close": df['close'].iloc[-1],
                "timestamp": df['timestamp'].iloc[-1],
                "agent": self.name,
                "from_cache": False
            }
            
            await event_bus.publish(EventType.MARKET_DATA, data)
            self.processed_count += 1

            # Persist to DB/cache
            self.persist_candles(symbol, timeframe, ohlcv)
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol} {timeframe}: {e}")
            await event_bus.publish(EventType.ERROR, {"agent": self.name, "symbol": symbol, "error": str(e)})

    async def handle_data_request(self, data: Dict[str, Any]):
        """Handle on-demand data requests from other agents (Task 5)"""
        if not self.is_active:
            return
            
        symbol = data.get('symbol')
        timeframe = data.get('timeframe', self.timeframe)
        requester = data.get('requester', 'Unknown')
        
        if symbol:
            logger.info(f"Received data request from {requester} for {symbol} {timeframe}")
            await self.fetch_and_publish(symbol, timeframe)

    def get_cached_data(self, symbol: str, timeframe: str) -> List:
        """Retrieve cached candles from database (Task 5)"""
        try:
            with SessionLocal() as db:
                candles = db.query(CandleModel).filter(
                    CandleModel.symbol == symbol,
                    CandleModel.timeframe == timeframe
                ).order_by(CandleModel.timestamp.asc()).limit(100).all()
                
                if candles:
                    return [[
                        int(c.timestamp.timestamp() * 1000),
                        c.open, c.high, c.low, c.close, c.volume
                    ] for c in candles]
                return None
        except Exception as e:
            logger.error(f"Cache read error: {e}")
            return None

    def is_cache_valid(self, cached_data: List, timeframe: str) -> bool:
        """Check if cached data contains the current candle (Task 5)"""
        if not cached_data:
            return False
        
        last_candle_time = cached_data[-1][0]  # timestamp in ms
        current_time = datetime.now().timestamp() * 1000
        
        # Get timeframe duration in ms
        tf_minutes = self._timeframe_to_minutes(timeframe)
        tf_ms = tf_minutes * 60 * 1000
        
        # Check if last candle is the current one
        time_diff = current_time - last_candle_time
        return time_diff < tf_ms

    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes"""
        multipliers = {'m': 1, 'h': 60, 'd': 1440, 'w': 10080}
        if len(timeframe) < 2:
            return 60  # Default
        try:
            return int(timeframe[:-1]) * multipliers.get(timeframe[-1], 60)
        except:
            return 60

    def persist_candles(self, symbol: str, timeframe: str, candles: List):
        """Persist candles to database cache (Task 5)"""
        try:
            with SessionLocal() as db:
                for c in candles:
                    ts = datetime.fromtimestamp(c[0] / 1000.0)
                    
                    existing = db.query(CandleModel).filter(
                        CandleModel.symbol == symbol,
                        CandleModel.timestamp == ts,
                        CandleModel.timeframe == timeframe
                    ).first()
                    
                    if not existing:
                        candle = CandleModel(
                            symbol=symbol,
                            timeframe=timeframe,
                            timestamp=ts,
                            open=c[1],
                            high=c[2],
                            low=c[3],
                            close=c[4],
                            volume=c[5]
                        )
                        db.add(candle)
                db.commit()
        except Exception as e:
             logger.error(f"Error persisting candles: {e}")

    async def stop(self):
        await super().stop()
        await self.exchange.close()
