# Priority Queue System Documentation

## Overview

The AiTrader event bus implements a priority queue system to ensure critical operations execute before less important ones. This guarantees that emergency stops, trade signals, and position management always take precedence over routine data fetching or logging.

## Priority Levels

The system defines 4 priority levels (lower values = higher priority):

### CRITICAL (Priority 0)
**Use for**: Emergency operations that require immediate execution
- Emergency stops
- Position closures
- System shutdown commands

### HIGH (Priority 1)
**Use for**: Trading operations and risk management
- Trade signals (STRATEGY_SIGNAL, SIGNAL)
- Order requests (ORDER_REQUEST)
- Order fills (ORDER_FILLED)
- Anomaly alerts (ANOMALY_ALERT)

### NORMAL (Priority 2)
**Use for**: Regular operations and data processing
- Market data events (MARKET_DATA)
- Market data requests (MARKET_DATA_REQUEST)
- Regime changes (REGIME_CHANGE)

### LOW (Priority 3)
**Use for**: Non-critical background operations
- Error logging (ERROR)
- System status updates (SYSTEM_STATUS)

## Event Processing Order

Events are processed in the following order:

1. **By Priority**: CRITICAL → HIGH → NORMAL → LOW
2. **Within Same Priority**: FIFO (First In, First Out)

This ensures that if an emergency stop is triggered while market data is being processed, the emergency stop will execute immediately, even if there are pending market data events.

## Architecture

### Event Wrapper

Each event is wrapped in an `Event` object that contains:
- `event_type`: The type of event
- `data`: Event payload
- `priority`: EventPriority enum value
- `timestamp`: Creation timestamp
- `agent_name`: Name of the agent that created the event

### Priority Queue

The `EventBus` uses `asyncio.PriorityQueue` to maintain event ordering. Events are:
1. Added to the queue with their priority
2. Automatically sorted by priority
3. Processed by a background task that dispatches to subscribers

### Event History

For debugging and UI display, the event bus maintains:
- **Global history**: Last 1000 events across all agents
- **Per-agent history**: Last 100 events per agent

## Usage Examples

### Default Priority (Automatic)

Most events use the default priority mapping:

```python
# Automatically assigned NORMAL priority
await event_bus.publish(EventType.MARKET_DATA, {
    "symbol": "BTC-USDT",
    "price": 50000
})
```

### Custom Priority Override

Override priority for special cases:

```python
from app.core.event_bus import EventPriority

# Force CRITICAL priority
await event_bus.publish(
    EventType.ORDER_REQUEST,
    {"symbol": "BTC-USDT", "side": "SELL"},
    priority=EventPriority.CRITICAL
)
```

## Performance Considerations

1. **Queue Processing**: Events are processed asynchronously in batches
2. **Subscriber Errors**: Individual subscriber errors don't block other subscribers
3. **Memory**: Event history is circular (fixed size) to prevent memory leaks
4. **Throughput**: Priority queue adds minimal overhead (~microseconds per event)

## Best Practices

1. **Use Default Priorities**: Let the system assign priorities unless you have a specific need
2. **Don't Abuse CRITICAL**: Reserve for truly emergency situations
3. **Group Related Events**: Events published together with the same priority maintain FIFO order
4. **Monitor Event History**: Use the agent events API to debug event flow issues

## Testing

Priority queue behavior can be tested using the DummyStrategyAgent:

```python
# Generate test events at different priorities
dummy_agent = DummyStrategyAgent(signal_interval=5)
await dummy_agent.start()

# Events will be processed in priority order regardless of creation order
```

## Future Enhancements

Potential improvements to the priority system:

- **Dynamic Priority Adjustment**: Adjust priorities based on system load
- **Priority Inheritance**: Child events inherit parent priority
- **Priority Metrics**: Track average processing time per priority level
- **Backpressure Handling**: Queue size limits with overflow strategies
