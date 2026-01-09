import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

class Settings(BaseModel):
    BINGX_API_KEY: str = os.getenv("BINGX_API_KEY", "")
    BINGX_SECRET_KEY: str = os.getenv("BINGX_SECRET_KEY", "")
    BINGX_IS_SANDBOX: bool = os.getenv("BINGX_IS_SANDBOX", "True").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./trading_bot.db")
    
    # Trading Parameters for MVP
    TRADING_SYMBOL: str = "BTC-USDT"
    TIMEFRAME: str = "1m"
    ORDER_SIZE_USDT: float = 10.0

settings = Settings()
