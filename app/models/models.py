from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

class CandleModel(Base):
    __tablename__ = "candles"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    timeframe = Column(String)
    timestamp = Column(DateTime, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

class SignalModel(Base):
    __tablename__ = "signals"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    signal_type = Column(String) # BUY, SELL, HOLD
    confidence = Column(Float)
    rationale = Column(String)
    price = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    strategy_id = Column(String)

class OrderModel(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    exchange_order_id = Column(String, unique=True, index=True)
    symbol = Column(String)
    side = Column(String)
    order_type = Column(String)
    amount = Column(Float)
    price = Column(Float)
    status = Column(String) # OPEN, FILLED, CANCELLED
    is_demo = Column(Integer, default=0) # 0 for live, 1 for demo
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String)
    agent_name = Column(String)
    data = Column(JSON)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class EquityModel(Base):
    __tablename__ = "equity_history"
    id = Column(Integer, primary_key=True, index=True)
    total_equity = Column(Float)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DemoBalanceModel(Base):
    __tablename__ = "demo_balance"
    id = Column(Integer, primary_key=True, index=True)
    balance = Column(Float, default=1000.0)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))
