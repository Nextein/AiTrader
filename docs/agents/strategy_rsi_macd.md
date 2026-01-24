# Strategy Agent: RSI & MACD

The **RSI_MACD Strategy Agent** is a "Mean Reversion" specialist. It looks for "overextended" prices that are likely to snap back to the average.

## Primary Responsibilities
1. **Oversold/Overbought Detection**: Uses the RSI indicator to find extremes.
2. **Momentum Confirmation**: Uses the MACD indicator to ensure the price is actually starting to turn around before issuing a signal.

## Internal Logic (Human Terms)

### 1. Identifying Extremes (RSI)
The agent looks for the **Relative Strength Index (RSI)** to reach specific levels:
*   **Below 35**: The asset is "oversold" (price has dropped too far, too fast).
*   **Above 65**: The asset is "overbought" (price has risen too far, too fast).

### 2. Confirming the Turn (MACD)
Just because an asset is oversold doesn't mean it will stop dropping. To avoid "catching a falling knife," the agent waits for a **MACD Cross**:
*   **For a BUY**: RSI must be < 35 **AND** the MACD line must cross above the Signal line.
*   **For a SELL**: RSI must be > 65 **AND** the MACD line must cross below the Signal line.

### 3. Signal Generation
If both conditions are met, the agent publishes a `STRATEGY_SIGNAL` with a base **confidence of 0.7**. It provides a "rationale" string explaining exactly why it likes the trade (e.g., "RSI is oversold (32.10) and MACD has crossed up").

## Key Events
| Event | Direction | Description |
| :--- | :--- | :--- |
| `MARKET_DATA` | **Input** | Receives enriched price data. |
| `STRATEGY_SIGNAL` | **Output** | Published when both RSI and MACD conditions are met. |
