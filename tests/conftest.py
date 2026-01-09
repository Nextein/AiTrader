import pytest
import asyncio
from app.core.event_bus import event_bus
from app.core.config import settings
import ccxt.async_support as ccxt
from unittest.mock import patch, AsyncMock, MagicMock

@pytest.fixture(autouse=True)
def reset_global_state():
    """Automatically resets global state between every test."""
    # Save original settings
    original_demo_mode = settings.DEMO_MODE
    
    # Global patch for ccxt to prevent any unmocked network activity.
    # We use a side_effect to ensure each call to bingx() gets a FRESH mock.
    def get_fresh_mock(*args, **kwargs):
        mock = AsyncMock()
        default_balance = {
            'total': {'USDT': 1000.0},
            'free': {'USDT': 1000.0},
            'USDT': {'total': 1000.0, 'free': 1000.0}
        }
        mock.fetch_balance.return_value = default_balance
        mock.fetch_ohlcv.return_value = [[i, 50, 51, 49, 50, 10] for i in range(100)]
        mock.fetch_positions.return_value = []
        mock.create_order.return_value = {'id': 'test-id', 'status': 'filled'}
        mock.cancel_all_orders.return_value = True
        return mock

    # Patch only the ccxt class. 
    # Do NOT patch demo_engine globally as it is needed for integration tests.
    with patch('ccxt.async_support.bingx', side_effect=get_fresh_mock):
        
        # Run the test
        yield
        
        # Restore settings
        settings.DEMO_MODE = original_demo_mode
        
        # Clear event bus subscribers
        event_bus.clear_subscribers()
