# Regime Detection Agent

The **Regime Detection Agent** is the system's "Market Context" analyzer. Its job is to determine if the market is currently **Trending** (moving strongly in one direction) or **Ranging** (moving sideways in a corridor).

## Primary Responsibilities
1. **Trend Strength Monitoring**: Analyzes the strength of price movements regardless of direction.
2. **Contextual Awareness**: Provides a "Regime" label that helps other agents (like the Aggregator) decide which strategies should be trusted more.

## Internal Logic (Human Terms)

### 1. The ADX Filter
The agent listens to the `MARKET_DATA` event. Every time new candles arrive, it calculates the **ADX (Average Directional Index)**.
*   **ADX** is a technical indicator that ranges from 0 to 100.
*   It does **not** indicate direction (Buy/Sell), only **strength**.

### 2. Decision Thresholds
The agent applies a simple but effective rule:
*   **If ADX > 25**: The market is declared **TRENDING**. This means there is a clear bias, and trend-following strategies (like EMA Crosses) are likely to perform better.
*   **If ADX <= 25**: The market is declared **RANGING**. This means the price is likely bouncing between support and resistance, and mean-reversion strategies (like RSI) are more reliable.

### 3. Change Alerts
The agent only publishes a `REGIME_CHANGE` event when the state actually flips. This prevents the system from "jittering" between states too frequently. When a change is detected, it "shouts" the new regime to the event bus, so the Aggregator can immediately adjust its weights.

## Key Events
| Event | Direction | Description |
| :--- | :--- | :--- |
| `MARKET_DATA` | **Input** | Receives enriched price data to perform analysis. |
| `REGIME_CHANGE` | **Output** | Published only when the market flips between TRENDING and RANGING. |
