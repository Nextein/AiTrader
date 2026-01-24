# Governor Agent

The **Governor Agent** is the "Conductor" of the orchestra. It doesn't analyze charts or place trades itself; instead, it manages the life and death of all other agents and keeps track of the system's overall health.

## Primary Responsibilities
1. **Agent Lifecycle Management**: Instantiates and "Starts" all other agents when the system boots up.
2. **Equity Tracking**: Periodically takes "snapshots" of the account balance to create performance charts.
3. **Emergency Coordination**: Can trigger a system-wide "Emergency Stop" if requested.

## Internal Logic (Human Terms)

### 1. Bootstrapping (The Big Bang)
When the AI Trader starts, the Governor is the first thing that loads. It looks at the configuration and creates "instances" of every other agent (Market, Risk, Strategy, etc.). It then tells each one to "Start" their internal loops.

### 2. Performance Snapshots
Every hour (or every minute in Demo/Sandbox mode), the Governor "pings" the exchange to see how much USDT is in the account. It saves this number to the `equity_history` table. This allows the user to see a graph of their balance growth (or decline) over time.

### 3. Graceful Shutdown
When a user wants to stop the bot, the Governor doesn't just "kill" the process. It sends a message to every agent telling them to "Stop" gracefully. This ensures that:
*   Market data agents close their API connections correctly.
*   The Risk agent doesn't start any new calculations.
*   The Execution agent finishes its current task.

### 4. Emergency Management
The Governor provides a "Master Switch." If an Emergency Stop is triggered, it publishes the `EMERGENCY_EXIT` event (which tells the Execution Agent to close all positions) and then immediately halts all other system logic.

## Key Events
| Event | Direction | Description |
| :--- | :--- | :--- |
| `EMERGENCY_EXIT` | **Output** | Published if a manual or automatic emergency stop is triggered. |
