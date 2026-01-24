# Audit Log Agent

The **Audit Log Agent** is the system's "Black Box Recorder." It records everything that happens on the Event Bus into a permanent database, ensuring full transparency and the ability to perform "forensic" analysis of any trade.

## Primary Responsibilities
1. **Total Visibility**: Listens to every single event type in the system (Market Data, Signals, Orders, Errors, etc.).
2. **Data Normalization**: Converts complex technical data (like NumPy arrays from the Market Data Agent) into standard JSON that can be saved in a database.
3. **Database Persistence**: Writes every event to the `audit_logs` table.

## Internal Logic (Human Terms)

### 1. The Super-Listener
Unlike other agents that only care about specific events (e.g., the Risk Agent only cares about Signals), the Audit Log Agent subscribes to **every single event** defined in the system.

### 2. Data Sanitization
Trading data is often full of "scientific" numbers (floats with 18 decimal places or special computer formats like `int64`). The agent carefully scans every piece of data and converts it into a clean, human-readable format before saving.

### 3. The Evidence Trail
Every entry in the database includes:
*   The **Event Type** (e.g., `STRATEGY_SIGNAL`).
*   The **Agent Name** that sent it.
*   The **Full Data Payload** (JSON).
*   A **Timestamp**.

This allows the UI Dashboard to show the "Live Audit Trail" and lets developers run queries like: *"Show me exactly what the RSI value was when the system decided to SELL BTC at 3:00 PM."*

## Key Events
| Event | Direction | Description |
| :--- | :--- | :--- |
| **ALL EVENTS** | **Input** | Subscribes to every event on the bus to record them. |
