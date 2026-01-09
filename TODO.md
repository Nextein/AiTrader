# Tasks

This is a list of tasks to be completed by the coding agent:

1. The buttons for each agent in the agents tab should display all events created by that agent.

2. The user should be able to activate and deactivate different strategy agents in the agents tab.

3. The user should be able to activate and deactivate different agents overall in the agents tab. Eventually there will be multiple risk agents for example with different risk profiles and logic, and multiple "workflows" will be running concurrently. The system architecture should allow for this growth and versatility in agent connection.

3. MarketData agent should constantly be spilling out data events for every symbol available in each exchange connected.

4. Market data is cached or stored in a database file to be reused later if any agent needs it to avoid having to refetch data. When a strategy requires data from another timeframe, it checks the db for it. If the last candle is the current candle it uses the cached data. If the last candle is not the one stored in the database it requests MarkeData to fetch it. MarketData agent would then publish a market data event like usual, apart from the strategy agent handling this data for its intended purposes.

5. Market data is fetched in order from higher timeframe to lower timeframe for each symbol. This way if a straategy requires a larger timeframe to handle an event on a smaller timeframe, it is likely to have the data available and up to date in the cache/db.

6. The event bus should have a priority queue so that agents are activated based on priority. Critical tasks such as opening or closing trades should execute before non-critical tasks such as fetching new market data. Prioritise everything accordingly and add documentation for this.

7. Create dummy agents that will test-run the system. For example a dummy strategy that gives a signal when it receives market data and gives another signal every 5 events after that. This will be helpful for debugging.

8. 