# Tasks

This is a list of tasks to be completed by the agent:

1. Change marketData event in UI to not display the candles data, only the symbol, timeframe and number of candles, or something similar that doesn't spam the UI so much but is still informative.
2. Complete the Agents tab in the UI:
    - Add detailed view for each agent (configuration, current state, performance).
    - Implement a "restart agent" button for individual agents.
    - Show real-time communication between agents (event flow).

## 🚀 Future Enhancements

### 🖥️ UI & Dashboard
- [ ] **Equity Curve**: Implement a real-time PnL tracker and equity curve visualization.

### 🧠 Backend & Orchestration
- [ ] **Multi-Symbol Support**: Update the Governor and Market Data agents to handle multiple trading pairs simultaneously.

### ⚖️ Risk & Execution
- [ ] **Dynamic Position Sizing**: Risk agent should calculate position size based on current portfolio balance and volatility (ATR).
- [ ] **Emergency Kill-Switch**: A global safety mechanism that closes all positions and stops all agents if drawdown exceeds a threshold.

### 🛠️ Infrastructure & Security
- [ ] **API Key Management**: Encrypt API keys at rest and implement a more secure way to handle secrets.


