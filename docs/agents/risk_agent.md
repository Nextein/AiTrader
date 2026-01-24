# Risk Agent

The **Risk Agent** is the system's "Safety Officer." Even if every strategy agrees on a trade, the Risk Agent has the final power to veto it or modify its size to protect the account balance.

## Primary Responsibilities
1. **Confidence Validation**: Ensures only high-confidence signals are processed (default threshold: 0.6).
2. **Account Protection**: Checks the current exchange balance before approving any trade.
3. **Dynamic Position Sizing**: Calculates the optimal amount of money to put into a trade based on current market volatility (ATR).

## Internal Logic (Human Terms)

### 1. The Confidence Gate
The agent first looks at the `confidence` score attached to the consensus `SIGNAL`. If the strategies reached a consensus but the score isn't strong enough (less than 0.6), the Risk Agent rejects the trade immediately.

### 2. Dynamic Position Sizing (The 2% Rule)
The system aims to lose no more than **2% of equity** on any single trade if the Stop Loss is hit. To do this, it uses a formula involving the **ATR (Average True Range)**:

*   **Volatility Check**: It calculates the current ATR to see how much the price is moving on average.
*   **Buffer**: It sets a "stop buffer" of **2x ATR**.
*   **Calculation**:
    1.  Target loss = `Account Balance * 0.02`.
    2.  Stop distance (as % of price) = `(2 * ATR) / Current Price`.
    3.  Trade Size = `Target Loss / Stop distance`.
*   **Cap**: It never allows a trade to exceed **10% of total equity**, regardless of what the formula says.

### 3. Order Generation
If the risk is within limits, it converts the USDT trade size into the "base amount" (e.g., number of BTC or ETH) and publishes an `ORDER_REQUEST` to the Execution Agent.

## Key Events
| Event | Direction | Description |
| :--- | :--- | :--- |
| `SIGNAL` | **Input** | Receives the consensus decision. |
| `MARKET_DATA` | **Input** | Uses the candle data to calculate current ATR. |
| `ORDER_REQUEST` | **Output** | Published if risk checks pass and position size is calculated. |
