# Strategy Agent: EMA Cross

The **EMA Cross Strategy Agent** is a "Trend Following" specialist. It ignores small price wobbles and looks for major shifts in market momentum.

## Primary Responsibilities
1. **Trend Identification**: Uses Exponential Moving Averages (EMAs) to determine the long-term flow of price.
2. **Entry Timing**: Identifies "Golden Crosses" and "Death Crosses" as entry signals.
3. **Risk Definition**: Automatically calculates initial Stop Loss (SL) and Take Profit (TP) levels for its signals.

## Internal Logic (Human Terms)

### 1. The Fast and the Slow
The agent uses two EMAs:
*   **Fast EMA (Period 9)**: Reacts quickly to recent price changes.
*   **Slow EMA (Period 21)**: Reflects the broader trend.

### 2. The Cross
Signals are generated when the Fast EMA "crosses" the Slow EMA:
*   **Golden Cross (BUY)**: When the 9 EMA crosses **above** the 21 EMA. This suggests momentum is shifting to the upside.
*   **Death Cross (SELL)**: When the 9 EMA crosses **below** the 21 EMA. This suggests momentum is shifting to the downside.

### 3. Automatic Protection
Unlike simple signal generators, this agent also proposes exit levels:
*   **Stop Loss (SL)**: Set at 2% away from the entry price.
*   **Take Profit (TP)**: Set at 5% away from the entry price.

### 4. Confidence
Because trend-following works best in "trending" markets, this agent starts with a base **confidence of 0.6**. This confidence is later adjusted by the **Aggregator Agent** depending on the current market regime.

## Key Events
| Event | Direction | Description |
| :--- | :--- | :--- |
| `MARKET_DATA` | **Input** | Receives enriched price data. |
| `STRATEGY_SIGNAL` | **Output** | Published when an EMA cross is detected. |
