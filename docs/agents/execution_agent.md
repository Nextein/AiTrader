# Execution Agent

The **Execution Agent** is the system's "Hands on the Keyboard." It is the only agent allowed to talk directly to the exchange to place or close orders.

## Primary Responsibilities
1. **Order Placement**: Executes Market, Limit, or Stop orders on BingX based on requests.
2. **Demo Mode Simulation**: Seamlessly switches between a simulated "Demo Engine" and the real exchange.
3. **Emergency Brake**: Listens for system-wide emergency alerts to close all positions instantly.
4. **Order Persistence**: Saves every successful execution into the database for tracking.

## Internal Logic (Human Terms)

### 1. Order Execution
When an `ORDER_REQUEST` arrives, the agent identifies if it's running in **DEMO** or **LIVE** mode.
*   **In Demo Mode**: It passes the request to an internal simulator that tracks "paper" profits and losses.
*   **In Live Mode**: It sends an authenticated API request to BingX to open a position with the specified amount, Stop Loss, and Take Profit.

### 2. The Emergency Circuit Breaker
If something goes wrong (e.g., Anomaly Detection triggers), the agent receives an `EMERGENCY_EXIT` event. It immediately:
1.  **Cancels** all open pending orders.
2.  **Fetches** all currently open positions.
3.  **Market Closes** every single position to move the account to "Flat" (cash only).

### 3. Monitoring SL/TP
In Demo Mode, the Execution Agent also monitors incoming `MARKET_DATA` to see if price has touched the Stop Loss or Take Profit of an existing trade. If so, it "fills" the exit and publishes an `ORDER_FILLED` event.

## Key Events
| Event | Direction | Description |
| :--- | :--- | :--- |
| `ORDER_REQUEST` | **Input** | Triggers the placement of a new trade. |
| `EMERGENCY_EXIT` | **Input** | Triggers the immediate closure of all positions. |
| `ORDER_FILLED` | **Output** | Published after a trade is successfully opened or naturally closed (SL/TP). |
