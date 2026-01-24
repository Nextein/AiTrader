# Strategy Agents

The AI Trader system supports multiple strategy agents operating in parallel. Each agent is responsible for analyzing market data and generating trade ideas (signals) based on its specific logic.

## Active Strategy Agents

1.  [**RSI & MACD Strategy**](./strategy_rsi_macd.md): A mean-reversion strategy that looks for overextended prices using the Relative Strength Index and confirms reversals with MACD crosses.
2.  [**EMA Cross Strategy**](./strategy_ema_cross.md): A trend-following strategy that generates signals based on the crossover of fast (9) and slow (21) Exponential Moving Averages.

## General Logic
All strategy agents follow a similar lifecycle:
*   **Listen**: They subscribe to the `MARKET_DATA` event.
*   **Analyze**: They calculate specific technical indicators using the incoming data.
*   **Evaluate**: They check if their specific entry criteria are met.
*   **Signal**: If conditions are met, they publish a `STRATEGY_SIGNAL` with a confidence score and a human-readable rationale.

## Signal Structure
Every strategy signal includes:
*   `symbol`: The trading pair (e.g., BTC/USDT).
*   `signal`: `BUY`, `SELL`, or `HOLD`.
*   `confidence`: A value between 0.0 and 1.0.
*   `rationale`: A text explanation of why the signal was generated.
*   `price`: The current market price.
*   `sl_price` / `tp_price`: Optional suggested Stop Loss and Take Profit levels.
