# Market Data Agent

The **Market Data Agent** is the system's primary data ingestion engine. It is responsible for fetching real-time and historical price data from the BingX exchange, calculating a rich set of technical indicators, and publishing this enriched data to the rest of the agent ecosystem.

## Primary Responsibilities
1. **Exchange Connection**: Maintains an asynchronous connection to BingX using the CCXT library.
2. **Multi-Symbol/Timeframe Support**: Iterates through all configured trading symbols and timeframes (e.g., 1m, 5m, 1h) to ensure the system has recent data.
3. **Indicator Calculation**: Transforms raw OHLCV (Open, High, Low, Close, Volume) data into a feature-rich dataset by applying complex technical analysis.
4. **Caching & Persistence**: Stores raw candle data in the database and uses local caching to avoid redundant API calls.
5. **On-Demand Data**: Responds to direct requests from other agents for specific market data.

## Internal Logic (Human Terms)

### 1. The Fetching Pulse
Every 10 seconds, the agent wakes up and checks if it needs new data. It prioritizes higher timeframes (like 1h) over lower ones (like 1m) to ensure macro trends are always up-to-date before micro analysis begins.

### 2. The Indicator Factory
When the agent receives a set of price candles, it doesn't just pass them on. It runs them through a "factory" that adds the following logic:

*   **Market Structure (HH/HL/LH/LL)**: It analyzes price peaks and valleys to identify "Higher Highs" (bullish), "Lower Lows" (bearish), and other structural shifts.
*   **Relative Candles**: It applies a specialized state machine that re-colors and re-defines candle opens and closes based on their relationship to previous candles. This helps filter out market "noise" and identifies clear "Up" or "Down" phases.
*   **Weis Waves**: It aggregates volume based on price direction. If the price is moving up, it sums the volume into a "Green Wave." If it reverses, it starts a "Red Wave." This reveals the true power behind price moves.
*   **Heikin Ashi**: It calculates "average" candles to smooth out price action and make trends easier to spot.
*   **Williams Fractals (S/R)**: It identifies "Fractals" (pivots where the middle candle is the highest/lowest of a 5, 7, or 9-candle range). These are then used to calculate the **Closest Support** and **Closest Resistance** levels.
*   **Trend & Volatility**: It calculates standard indicators like **ADX** (trend strength), **ATR** (volatility), and multiple **EMAs** (9, 21, 55, 144, 252).
*   **Volume Analysis**: It calculates **OBV** (On-Balance Volume) and **CVD** (Cumulative Volume Delta) to track buying vs. selling pressure.

### 3. Smart Caching
Before hitting the exchange API, the agent checks the local database. If the latest candle in the database is still "fresh" (within the timeframe window), it uses the cached data instead of wasting API rate limits.

## Key Events
| Event | Direction | Description |
| :--- | :--- | :--- |
| `MARKET_DATA` | **Output** | Published after every successful fetch, containing the enriched DataFrame. |
| `MARKET_DATA_REQUEST` | **Input** | Triggered by other agents needing specific data immediately. |
| `ERROR` | **Output** | Published if an API call or indicator calculation fails. |
