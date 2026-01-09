
## 🚀 Future Enhancements

Do not implement any of these yet.

### ⚖️ Risk & Execution
- [ ] **Dynamic Position Sizing**: Risk agent should calculate position size based on current portfolio balance and volatility (ATR).


3. The user should be able to activate and deactivate different agents overall in the agents tab. Eventually there will be multiple risk agents for example with different risk profiles and logic, and multiple "workflows" will be running concurrently. The system architecture should allow for this growth and versatility in agent connection.


# Tests
9. Increase code coverage of tests. Do not be shy with the number of tests created.
10. Increase branch coverage of tests.
11. Increase function coverage of tests.
12. Increase line coverage of tests.
13. Increase statement coverage of tests.
14. Increase condition coverage of tests.
15. Increase mutation coverage of tests.
16. Increase path coverage of tests.
17. Increase complexity coverage of tests.
18. 


# Analyst AI Agent

I am running Ollama in my windows laptop where I am running the AITrader. I am running it on port 11434. I have the following models downloaded because they are the best I could find given my hardware constraints:

daryltucker/Mistral-v0.3-Instruct:7B-FP32
deepseek-coder:1.3b
phi3:mini
qwen3-coder:30b
qwen3:4b

I'd like to add an analyst agent that can analyze the market and trade based on the analysis performed.

To do so it must have access several things. The analyst agent should be able to receive market data along with many indicators calculated on it, possibly in some form of pandas data frame containing price and a column for each indicator. The analyst should also be aware of trading strategies and trading principles to apply stored in some form of prompt in markdown text so that it knows what it needs to do with this information. I will pass it a set of principles on different ways it can analyze the market as well as different strategies that it can apply and the analyst should reference this properly to make a decision on what trades the place. Based on what it is seeing in the market, different strategies can be applied using the analyst's agent's discretion but it should always follow the way of trading that I have taught it, you could say. It can feed from any other agent for any information that it needs, such as maybe asking the regime change agent what the current regime is for a certain symbol which I assume it would just find this in the database as opposed to actually asking the regime change agent since the regime change agent runs and updates the current state on every market data event. It should also be able to ask the risk agent for information on the current risk profile and the current position sizes (ideally stored in the database as opposed to having to request it from the risk agent).