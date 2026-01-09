# Tasks

This is a list of tasks to be completed by the coding agent:

1. Display the current portfolio in the UI.
2. In the performance tab add a table with every trade placed. For each trade it should display whether it was a buy or sell, the SL and TP values, the entry price and the exit price, pnl, date and time of the trade, reason, and any other information you consider relevant.
3. Strategy signals must provide SL and TP values. Risk Agent is the enforcer of this rule and ignores signals that do not meet these requirements.
4. SL and TP values can be relative to the entry price or absolute values. They can also be partial or full, allowing for multiple TPs or SLs to be set for a given entry.
5. demo engine checks whether these SLs and TPs have been hit to update the demo balance.
6. Market regime agent should look at multiple timeframes and indicators to determine market regime for each symbol.
7. Displaying market regime in the UI as a single value no longer makes sense if there are many symbols being traded. It should be displayed as a table with the market regime for each symbol.
8. Event logs in the frontend should be made to be more beautiful and not just display the raw event data for each event. Market data events have already been made more beautiful, but the others have not. Implement this feature.
