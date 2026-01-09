import logging
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from app.core.database import SessionLocal
from app.models.models import DemoBalanceModel, OrderModel
from app.core.config import settings

logger = logging.getLogger("DemoEngine")

class DemoEngine:
    def __init__(self, db_session=None):
        self.name = "DemoEngine"
        self._db_session = db_session

    def _get_db(self):
        if self._db_session:
             from contextlib import contextmanager
             @contextmanager
             def wrapper():
                 yield self._db_session
             return wrapper()
        return SessionLocal()

    async def initialize_balance(self):
        """Ensures the demo balance is initialized in the database."""
        """Ensures the demo balance is initialized in the database."""
        with self._get_db() as db:
            existing = db.query(DemoBalanceModel).first()
            if not existing:
                new_balance = DemoBalanceModel(balance=settings.INITIAL_DEMO_BALANCE)
                db.add(new_balance)
                db.commit()
                logger.info(f"DemoEngine: Initialized demo balance with {settings.INITIAL_DEMO_BALANCE} USDT")

    async def fetch_balance(self):
        """Retrieves the current demo balance."""
        with self._get_db() as db:
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
        
        with self._get_db() as db:
            # Update balance
            record = db.query(DemoBalanceModel).first()
            cost = amount * fill_price
            
            if side.lower() == 'buy':
                record.balance -= cost
            else:
                record.balance += cost
                
            record.last_updated = datetime.now(timezone.utc)
            
            # Extract SL/TP/Rationale from params
            sl_price = params.get('sl_price') if params else None
            tp_price = params.get('tp_price') if params else None
            rationale = params.get('rationale') if params else None

            # Record order
            order = OrderModel(
                exchange_order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=type,
                amount=amount,
                price=fill_price,
                sl_price=sl_price,
                tp_price=tp_price,
                rationale=rationale,
                status='FILLED', # In this simple demo, market orders fill immediately
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

    async def check_sl_tp(self, market_data):
        """Checks if any open positions have hit SL or TP."""
        symbol = market_data.get('symbol')
        current_price = market_data.get('latest_close')
        timestamp = market_data.get('timestamp')
        
        if not symbol or not current_price:
            return

        with self._get_db() as db:
            # Find OPEN positions? 
            # In our simple model, 'FILLED' orders are open positions until we 'close' them.
            # We need a way to track which orders are still "open" positions.
            # A better way for this MVP is to look for orders with status 'FILLED' that haven't been 'closed' or netted out.
            # BUT, the current schema doesn't link filling and closing.
            # Lets assume we check all FILLED orders that don't have a 'closed_at' timestamp.
            # Since we just added 'closed_at', let's use that.
            
            open_orders = db.query(OrderModel).filter(
                OrderModel.symbol == symbol,
                OrderModel.status == 'FILLED',
                OrderModel.closed_at.is_(None),
                OrderModel.is_demo == 1
            ).all()

            for order in open_orders:
                sl_hit = False
                tp_hit = False
                exit_reason = None
                
                # Check SL
                if order.sl_price:
                    sl_list = order.sl_price if isinstance(order.sl_price, list) else [order.sl_price]
                    # Logic: if Long, SL is below. If Short, SL is above.
                    if order.side == 'buy':
                        if any(current_price <= float(sl) for sl in sl_list):
                            sl_hit = True
                            exit_reason = "Stop Loss Hit"
                    else: # sell
                        if any(current_price >= float(sl) for sl in sl_list):
                            sl_hit = True
                            exit_reason = "Stop Loss Hit"
                
                # Check TP (only if SL not hit)
                if not sl_hit and order.tp_price:
                    tp_list = order.tp_price if isinstance(order.tp_price, list) else [order.tp_price]
                    if order.side == 'buy':
                        if any(current_price >= float(tp) for tp in tp_list):
                            tp_hit = True
                            exit_reason = "Take Profit Hit"
                    else: # sell
                        if any(current_price <= float(tp) for tp in tp_list):
                            tp_hit = True
                            exit_reason = "Take Profit Hit"
                
                if sl_hit or tp_hit:
                    # Execute Close
                    await self._close_position(db, order, current_price, exit_reason, timestamp)

    async def _close_position(self, db, order, exit_price, reason, timestamp):
        """Closes a position in the DB and updates balance."""
        logger.info(f"DEMO: closing position {order.id} ({order.symbol}) due to {reason} at {exit_price}")
        
        # Calculate PnL
        # Long: (Exit - Entry) * Amount
        # Short: (Entry - Exit) * Amount
        if order.side == 'buy':
            pnl = (exit_price - order.price) * order.amount
        else:
            pnl = (order.price - exit_price) * order.amount
            
        # Update Balance
        balance_record = db.query(DemoBalanceModel).first()
        if balance_record:
            balance_record.balance += pnl
            # Note: We already deducted cost when buying. 
            # Wait, standard accounting: 
            # Long Buy: Balance - Cost. Sell: Balance + Revenue. Profit = Revenue - Cost.
            # Short Sell: Balance + Revenue? No, margin trading is different.
            # Simplified Demo Mock:
            # We adjusted balance by 'cost' at entry.
            # If Buy: Balance -= Price * Amount.
            # Now Sell: Balance += ExitPrice * Amount.
            # Net change = (Exit - Entry) * Amount.
            
            # If Sell (Short):
            # We added cost? 
            # let's look at create_order: 
            # if side == 'buy': record.balance -= cost
            # else: record.balance += cost 
            # This logic for 'sell' implies we received cash. (Spot sell).
            # If it's a SHORT (margin), we shouldn't receive full notional.
            # But let's stick to the logic already in create_order. 
            # If we sold to open (short?), we gained cash? 
            # If we are closing a short, we are BUYING back.
            
            cost_at_exit = exit_price * order.amount
            if order.side == 'buy':
                # We are selling now
                balance_record.balance += cost_at_exit
            else:
                # We are buying back (closing short)
                # entry: balance += entry_cost.
                # exit: balance -= exit_cost.
                balance_record.balance -= cost_at_exit
                
            balance_record.last_updated = datetime.now(timezone.utc)
            
        # Update Order Record
        order.status = 'CLOSED'
        order.exit_price = exit_price
        order.pnl = pnl
        order.closed_at = datetime.now(timezone.utc) # Use proper naive/aware? Config uses utc
        order.rationale = f"{order.rationale} | {reason}" if order.rationale else reason
        
        db.commit()
        
        # We should probably publish an event too?
        # Maybe later.

demo_engine = DemoEngine()
