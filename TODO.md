# Tasks

## Completed

- [x] When running the system, many timeframes aren't fetched and I can see symbols with timeframes that are null. Fixed by implementing retry logic in Market Data Agent with exponential backoff.
- [x] Open Positions in UI dashboard don't display last price and pnl, it shows -- instead. Fixed by enhancing the /portfolio endpoint to calculate unrealized PnL.
- [x] Fix terminal errors:
    - name 'AnalysisManager' is not defined in RegimeDetectionAgent.
    - KeyError 'latest_close' in event handlers.
    - object of type 'NoneType' has no len() in various agents.
- [x] Implementation of Value Areas Agent: 
    - Calculates Volume Profile, POC, VAH/VAL according to theory.
    - Detects SFP (Swing Failure Patterns) and Failed Auctions.
    - Integrated as a new section in AnalysisObject and registered in GovernorAgent before MarketStructureAgent.
