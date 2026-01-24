# Tasks

## analysis object

All data related to a symbol should be stored in a single object for that symbol. The object should contain data according to the specified analysis JSON schema in app/models/analysis.json

All agents receive this object when doing anything related to the symbol.

All agents edit this object when doing anything related to the symbol. Each agent knows which section is is in charge of filling in and updating, as well as which sections it is interested in looking at.

Create this analysis object in a way that makes it shareable across agents without read and write conflicts such that they all have the latest version of the data when they need it or read it, and they can all write to it.


The agents I would like to implement are the following:

1. Regime Change Agent
2. Support and Resistance Agent
3. Analyst Agent
4. Market Structure Agent
5. VWAP Agent
6. Volume Profile Agent
7. Fibonacci Retracement Agent
8. Value Areas Agent


Information on each agent is provided in docs/agents/agent_name.md

But for now, to simplify the task, being by implementing only two of the Agents: the Market Data Agent and the Market Structure Agent.

The Market Data Agent is already mostly implemented, but it needs to be updated to use the new analysis object and store the data in this object. It should also publish events to the event bus when it updates the market data for a symbol, I don't know if the current publishing needs any changes to accommodate this new architecture.

The Market Data Agent fills in the market_data section with all the indicator columns it currently has. It stores one dataframe per timeframe.

The market structure agent listens to market data events for a symbol and updates the market structure of that symbol in the analysis object for that symbol and timeframe. Specifically it must set the market_structure.highs, lows, pivot_points and emas values. More detailed information on the prompt for the Market Data Agent is provided in docs/agents

The prompts are not well written. In terms of any LLMs needed, I am running an ollama instance locally, available on the usual port. Use Langchain if needed to interface with it.