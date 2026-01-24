import os
from dotenv import load_dotenv
from pydantic import BaseModel
from cryptography.fernet import Fernet

load_dotenv()

def decrypt_secret(secret_raw: str):
    if not secret_raw or not secret_raw.startswith("ENCR:"):
        return secret_raw
    
    key = os.getenv("SECRET_ENCRYPTION_KEY")
    if not key:
        return secret_raw # Fallback or Raise Error
    
    try:
        f = Fernet(key.encode())
        return f.decrypt(secret_raw[5:].encode()).decode()
    except Exception:
        return secret_raw

class Settings(BaseModel):
    BINGX_API_KEY: str = decrypt_secret(os.getenv("BINGX_API_KEY", ""))
    BINGX_SECRET_KEY: str = decrypt_secret(os.getenv("BINGX_SECRET_KEY", ""))
    BINGX_IS_SANDBOX: bool = os.getenv("BINGX_IS_SANDBOX", "True").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./trading_bot.db")
    
    # Trading Parameters for MVP
    TRADING_SYMBOLS: list = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
    TIMEFRAME: str = "1m"
    TIMEFRAMES: list = ["1w", "1d", "4h", "1h", "30m", "15m", "5m"]
    ORDER_SIZE_USDT: float = 10.0
    
    # Demo Mode
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "False").lower() == "true"
    INITIAL_DEMO_BALANCE: float = float(os.getenv("INITIAL_DEMO_BALANCE", "1000.0"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

settings = Settings()
