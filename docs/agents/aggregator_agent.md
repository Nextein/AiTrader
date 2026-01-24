# Aggregator Agent

The **Aggregator Agent** is the system's "Consensus Engine." It acts as a judge, weighing the opinions of different strategies and deciding if the system should actually place a trade.

## Primary Responsibilities
1. **Signal Buffering**: Waits for a fixed window (default: 5 seconds) after the first signal arrives to see if other strategies agree.
2. **Consensus Building**: Uses "Regime-Adaptive Weighting" to calculate a final consensus score.
3. **Filtering**: Rejects trades where strategies are conflicting (e.g., one says BUY, one says SELL).

## Internal Logic (Human Terms)

### 1. The Waiting Room
Technical indicators often trigger at slightly different times even on the same candle. To handle this, the Aggregator doesn't act instantly. When it hears a `STRATEGY_SIGNAL`, it opens a "buffer window" for that timestamp and waits.

### 2. Regime-Adaptive Weighting
This is the "secret sauce" of the system. The Aggregator knows whether the market is **TRENDING** or **RANGING** (thanks to the Regime Detection Agent). It adjusts the importance (weight) of each strategy accordingly:

*   **In a TRENDING Market**:
    *   **EMA Cross** strategy gets **1.5x** more weight (it's a trend follower).
    *   **RSI_MACD** strategy gets **0.5x** less weight (it might prematurely call a reversal).
*   **In a RANGING Market**:
    *   **RSI_MACD** strategy gets **1.5x** more weight (it excels at finding bounce points).
    *   **EMA Cross** strategy gets **0.5x** less weight (it often gets "chopped up" in sideways markets).

### 3. The Consensus Score
The agent calculates a score between **-1.0 (Strong SELL)** and **1.0 (Strong BUY)**.
*   **Weighted Sum / Total Weight = Score**
*   **If Score > 0.3**: Confirms a **BUY** signal.
*   **If Score < -0.3**: Confirms a **SELL** signal.
*   **If Score is between -0.3 and 0.3**: The system is "unsure" and issues a **HOLD**.

### 4. Selecting Parameters
If a consensus is reached, the Aggregator picks the SL/TP prices from one of the "source" signals (the one that matches the final decision) and publishes a final `SIGNAL`.

## Key Events
| Event | Direction | Description |
| :--- | :--- | :--- |
| `STRATEGY_SIGNAL` | **Input** | Receives signals from individual strategy agents. |
| `REGIME_CHANGE` | **Input** | Updates the internal weighting multipliers. |
| `SIGNAL` | **Output** | Published only if the consensus score clears the threshold. |


# Prompt

