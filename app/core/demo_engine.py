import logging
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from app.core.database import SessionLocal
from app.models.models import DemoBalanceModel, OrderModel
from app.core.config import settings

logger = logging.getLogger("DemoEngine")

class DemoEngine:
    def __init__(self):
        self.name = "DemoEngine"

    async def initialize_balance(self):
        """Ensures the demo balance is initialized in the database."""
        with SessionLocal() as db:
            existing = db.query(DemoBalanceModel).first()
            if not existing:
                new_balance = DemoBalanceModel(balance=settings.INITIAL_DEMO_BALANCE)
                db.add(new_balance)
                db.commit()
                logger.info(f"DemoEngine: Initialized demo balance with {settings.INITIAL_DEMO_BALANCE} USDT")

    async def fetch_balance(self):
        """Retrieves the current demo balance."""
        with SessionLocal() as db:
            record = db.query(DemoBalanceModel).first()
            balance = record.balance if record else settings.INITIAL_DEMO_BALANCE
            return {
                'total': {'USDT': balance},
                'free': {'USDT': balance}, # For simplicity, all balance is free
                'USDT': {'total': balance, 'free': balance}, # CCXT style convenience key
                'info': {'data': {'balance': balance}} # BingX-like compatibility
            }

    async def create_order(self, symbol, type, side, amount, price=None, params=None):
        """Simulates a market order execution."""
        # In a real system, we'd fetch the latest price from MarketDataAgent or a ticker
        # For this implementation, we'll assume the price is passed or we'll need to fetch it.
        # Since ExecutionAgent currently doesn't pass price for market orders, 
        # let's assume market orders fill at the 'price' if provided, or we need a way to get it.
        
        fill_price = price if price else 0.0 # Will be updated by ExecutionAgent logic or fetched
        
        # In this demo engine, we'll just record it.
        # ExecutionAgent will be responsible for providing the latest price for demo orders.
        
        order_id = f"demo-{uuid4()}"
        
        with SessionLocal() as db:
            # Update balance
            record = db.query(DemoBalanceModel).first()
            cost = amount * fill_price
            
            if side.lower() == 'buy':
                record.balance -= cost
            else:
                record.balance += cost
                
            record.last_updated = datetime.now(timezone.utc)
            
            # Record order
            order = OrderModel(
                exchange_order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=type,
                amount=amount,
                price=fill_price,
                status='FILLED',
                is_demo=1
            )
            db.add(order)
            db.commit()
            
        logger.info(f"DEMO ORDER FILLED: {order_id} | {side.upper()} {amount} {symbol} @ {fill_price}")
        
        return {
            'id': order_id,
            'symbol': symbol,
            'type': type,
            'side': side,
            'amount': amount,
            'price': fill_price,
            'status': 'closed', # CCXT standard
            'timestamp': int(datetime.now(timezone.utc).timestamp() * 1000)
        }

    async def fetch_positions(self):
        """Stub for positions."""
        return []

    async def cancel_all_orders(self):
        """Stub for cancelling orders."""
        return True

    async def close(self):
        """Stub for closing session."""
        pass

demo_engine = DemoEngine()
