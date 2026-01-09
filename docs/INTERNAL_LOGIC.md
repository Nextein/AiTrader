# ChartChampion AI: Internal Logic & Traceability

This document explains how the Multi-Agent System (MAS) operates under the hood, how agents communicate, and how you can achieve full traceability of every decision.

## 1. The Core: Event-Driven Architecture

The system is built on an **Event Bus** (Pub/Sub pattern). No agent calls another agent directly. Instead, they "shout" events into the bus, and anyone interested "listens."

### Key Event Types:
- `MARKET_DATA`: Raw price/volume info.
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

### Step 2: Intelligence & Analysis (Parallel)
- **Agent**: `RegimeDetectionAgent`
  - Listens to: `MARKET_DATA`
  - Action: Runs ADX/ATR to find the regime.
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

### A. Terminal Logs (Real-time)
We promoted debugging logs to `INFO`. You can see exactly what each indicator is doing:
```bash
[MarketDataAgent] [BTC-USDT] Fetched 100 candles. Latest Close: 87560.9
[RegimeDetectionAgent] Market Monitoring: ADX=16.81 | Current Regime=RANGING
[StrategyAgent_RSI_MACD] Indicators >> RSI: 42.10 | MACD: -0.05
[AggregatorAgent] Buffered signal from RSI_MACD for processing.
[AuditLogAgent] [PERSISTED] Event: market_data from unknown
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
