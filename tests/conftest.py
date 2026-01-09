import pytest
from app.core.event_bus import event_bus
from app.core.config import settings

@pytest.fixture(autouse=True)
def reset_global_state():
    """Automatically resets global state between every test."""
    # Save original settings
    original_demo_mode = settings.DEMO_MODE
    
    # Run the test
    yield
    
    # Restore settings
    settings.DEMO_MODE = original_demo_mode
    
    # Clear event bus subscribers
    event_bus.clear_subscribers()
    
    # Additional cleanup if needed
