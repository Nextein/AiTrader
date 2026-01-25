# ChartChampion AI: Internal Logic & Traceability

This document explains how the Multi-Agent System (MAS) operates under the hood, how agents communicate, and how you can achieve full traceability of every decision.

## 1. The Core: Event-Driven Architecture

The system is built on an **Event Bus** (Pub/Sub pattern). No agent calls another agent directly. Instead, they "shout" events into the bus, and anyone interested "listens."

### Key Event Types:
- `MARKET_DATA`: Raw price/volume info.
- `VALUE_AREAS_UPDATED`: Point of Control and Value Area calculations completed.
- `ANALYSIS_UPDATE`: Specific analysis section (e.g., market_structure) has been updated.
- `REGIME_CHANGE`: Classification of market state (Trending/Ranging).
- `STRATEGY_SIGNAL`: Individual strategy outputs (RSI, EMA, etc.).
- `SIGNAL`: The final, aggregated decision after consensus.
- `ORDER_REQUEST`: An approved signal waiting for execution.
- `ORDER_FILLED`: Confirmation of a successful trade.

---

## 2. Orchestration: The Governor

The **Governor Agent** (`app/agents/governor_agent.py`) is the conductor. It:
1.  **Instantiates** all other agents (Market, Strategy, Aggregator, Risk, Execution, Audit, Anomaly).
2.  **Starts** each agent's custom `run_loop`.
3.  **Monitors** for failures.

The system is triggered via `app/main.py`, which is a FastAPI server. When you hit the `/start` endpoint, the Governor begins the cycle.

---

## 3. Step-by-Step Flow (The "Trading Pulse")

Every 10-60 seconds, the following cycle triggers:

### Step 1: Ingestion
- **Agent**: `MarketDataAgent`
- **Action**: Fetches OHLCV from BingX.
- **Trace**: "Fetched 100 candles..."
- **Output**: Publishes `MARKET_DATA`.

### Step 2: Intelligence & Analysis (Sequential & Parallel)
- **Agent**: `ValueAreasAgent`
  - Listens to: `MARKET_DATA`
  - Action: Calculates VPVR, POC, and Value Areas.
  - Output: Publishes `VALUE_AREAS_UPDATED`.
- **Agent**: `MarketStructureAgent`
  - Listens to: `VALUE_AREAS_UPDATED`
  - Action: Analyzes POC trends (ASCENDING/DESCENDING) over the last 3 windows.
  - Output: Updates `market_structure` and publishes `ANALYSIS_UPDATE`.
- **Agent**: `RegimeDetectionAgent`
  - Listens to: `ANALYSIS_UPDATE`
  - Action: Runs ADX/ATR and combines with POC trends for final regime classification.
  - Trace: "Regime Change Detected: TRENDING -> RANGING"
- **Agent**: `StrategyAgents` (RSI/MACD, EMA Cross)
  - Listen to: `MARKET_DATA`
  - Action: Calculate indicators.
  - Trace: "[RSI_MACD] Indicators >> RSI: 45.2 ... [HOLD]"
  - Output: Publishes `STRATEGY_SIGNAL` (if criteria met).

### Step 3: Consensus
- **Agent**: `AggregatorAgent`
  - Listens to: `STRATEGY_SIGNAL` and `REGIME_CHANGE`.
  - Action: Buffers signals for 5 seconds. If in `RANGING` regime, it gives higher weight to RSI. If `TRENDING`, it favors EMA Cross.
  - Output: Publishes `SIGNAL`.

### Step 4: Safety & Risk
- **Agent**: `RiskAgent`
  - Listens to: `SIGNAL`
  - Action: Checks BingX balance. If balance < trade size, it rejects.
  - Output: Publishes `ORDER_REQUEST`.
- **Agent**: `AnomalyDetectionAgent`
  - Listens to: `SIGNAL` & `MARKET_DATA`
  - Action: Monitors for flash crashes or "spam" signals (circuit breaker).

### Step 5: Final Execution
- **Agent**: `ExecutionAgent`
  - Listens to: `ORDER_REQUEST`
  - Action: Hits the BingX API to open a position.
  - Output: Publishes `ORDER_FILLED`.

---

## 3. How to Achieve Full Traceability

The system generates a triple-layer trail for every single tick:

We use a standardized logging system in `BaseAgent` (`app/agents/base_agent.py`) that ensures consistency across the MAS. Agents should use:
- `self.log(message, level)`: Basic logging with standard prefix.
- `self.log_llm_call(prompt, symbol, result)`: Tracks model interactions.
- `self.log_market_action(action, symbol, data)`: Tracks data fetches and structural updates.

Example log output:
```bash
[MarketDataAgent] MARKET_ACTION: FETCH_DATA_LIVE for BTC-USDT | DATA: {'timeframe': '1h'}
[ValueAreasAgent] MARKET_ACTION: CALCULATE_VALUE_AREAS for BTC-USDT | DATA: {'timeframe': '1h', 'state': 'IN', 'poc': 87450.5}
[MarketStructureAgent] Received value areas update for BTC-USDT 1h
[MarketStructureAgent] MARKET_ACTION: UPDATE_STRUCTURE for BTC-USDT | DATA: {'timeframe': '1h', 'va_state': 'ASCENDING'}
[RegimeDetectionAgent] LLM_CALL: regime_decision for BTC-USDT | DATA: {'timeframe': '1h', 'regime': 'BULLISH'}
```

### B. Dashboard Trace (Visual)
The "Live Audit Trail" on the dashboard (`/static/index.html`) queries the database every 3 seconds. It shows JSON data for every event, allowing you to see the `rationale` string provided by the agents.

### C. Database (Deep Forensic)
Every event is saved in the `audit_logs` table. You can query it via SQL to see why a trade was (or wasn't) taken:
```sql
SELECT agent_name, event_type, data FROM audit_logs ORDER BY timestamp DESC LIMIT 20;
```

## 4. Troubleshooting
If you only see `market_data` and `regime_change`:
1. **Conditions not met**: Check the strategy agents' logs. If RSI is 50, the `StrategyAgent` won't publish a signal.
2. **Confidence**: The `Aggregator` requires a consensus score > 0.3. If strategies conflict (one says BUY, one says SELL), it results in a `HOLD`.
3. **Weighting**: In a `RANGING` market, a trend-following signal (EMA) will have its confidence reduced by the Aggregator.
