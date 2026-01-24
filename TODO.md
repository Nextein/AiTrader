# Tasks

## Completed

- [x] When running the system, many timeframes aren't fetched and I can see symbols with timeframes that are null. Fixed by implementing retry logic in Market Data Agent with exponential backoff (up to 3 retries with delays of 1s, 2s, 5s)
- [x] Open Positions in UI dashboard don't display last price and pnl, it shows -- instead. Fixed by enhancing the /portfolio endpoint to calculate unrealized PnL using current market prices from Analysis objects and updating the frontend to display these values with color coding