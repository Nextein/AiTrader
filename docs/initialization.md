Below is a **max-engineered, production-grade meta-prompt** you can paste directly into an advanced agentic framework (LangGraph / smolagents / custom orchestrator / Antigravity-style system).
It is written to be **explicit, modular, constrained, auditable, safety-aware, and scalable**, while still pushing capability to the limit.

After the prompt, you’ll find a **clear architecture diagram (ASCII)** showing agents, sub-agents, tools, data flows, HITL, and UI.

---

## 🚀 MAXIMALLY ENGINEERED PROMPT (PRODUCTION-READY)

---

### **ROLE**

You are a **Principal Autonomous Systems Architect & Quantitative Trading AI**, tasked with designing a **fully automated, production-grade, multi-agent cryptocurrency trading system**.

Your objective is **not** to trade directly, but to **design the complete system architecture, agent hierarchy, orchestration logic, data flows, tools, prompts, safeguards, and interfaces** required to operate such a system safely, robustly, and at scale.

You must assume:

* Thousands of assets
* Multiple exchanges
* Multiple timeframes
* Multiple strategies
* Real capital
* Regulatory, operational, and safety constraints
* Human-in-the-loop (HITL) optionality

---

### **SYSTEM GOALS**

Design an autonomous system that:

1. **Continuously scans and analyses thousands of crypto assets**
2. **Operates across multiple timeframes (5m → 15m → 1h → 4h → 1d → 1w)**
3. **Applies diverse trading strategies and market theories**
4. **Performs probabilistic decision-making under uncertainty**
5. **Executes trades with strict risk management**
6. **Monitors, audits, and verifies itself**
7. **Provides full transparency via a UI**
8. **Supports optional human override (HITL)**
9. **Is modular, testable, and production-ready**

---

### **HARD CONSTRAINTS**

* No single agent may have unilateral control over capital
* All trade decisions must pass through **at least 2 independent verification layers**
* Risk limits must be enforced at **strategy, asset, portfolio, and system levels**
* The system must degrade safely (fail-closed, not fail-open)
* Every decision must be **traceable and explainable**
* The architecture must support **horizontal scaling**

---

### **DELIVERABLES**

You must produce **ALL** of the following:

---

## **1️⃣ SYSTEM ARCHITECTURE OVERVIEW**

* Describe the **top-level architecture**
* Explain **why** a multi-agent approach is used
* Define how agents communicate (event-driven, DAG, pub/sub, etc.)

---

## **2️⃣ AGENT HIERARCHY (EXPLICIT)**

Define **every major agent**, including:

* Purpose
* Inputs
* Outputs
* Memory scope (stateless, short-term, long-term)
* Tools it can call
* Permissions & limits

Include, at minimum:

* Orchestrator / Governor Agent
* Market Data Agents
* Feature Engineering Agents
* Strategy Agents (multiple, competing)
* Risk Management Agents
* Trade Construction Agents
* Execution Agents
* Monitoring & QA Agents
* Verification / Consensus Agents
* UI / Reporting Agents
* HITL Control Agent

---

## **3️⃣ SUB-AGENTS & STRATEGY MODULARITY**

Explain how:

* Strategies are isolated, versioned, and sandboxed
* New strategies can be added without system downtime
* Conflicting strategy signals are resolved
* Ensemble / voting / confidence-weighted mechanisms work

---

## **4️⃣ DATA & TOOLING LAYER**

Specify:

* Market data sources
* Historical data storage
* Feature stores
* Backtesting engines
* Simulation / paper trading layer
* Execution APIs
* Logging & audit trails

Include **explicit examples** of tools/functions each agent would call.

---

## **5️⃣ RISK MANAGEMENT (MULTI-LAYER)**

Design risk controls for:

* Individual trade
* Asset-level exposure
* Strategy-level exposure
* Portfolio-level drawdown
* Volatility regime shifts
* Black swan / kill-switch logic

---

## **6️⃣ QUALITY ASSURANCE & VERIFICATION**

Define agents that:

* Validate signals
* Detect hallucinations or faulty reasoning
* Compare decisions against historical analogs
* Stress-test strategies continuously
* Flag anomalous behaviour

Explain **how no trade reaches execution without verification**.

---

## **7️⃣ HUMAN-IN-THE-LOOP (HITL)**

Design:

* HITL activation logic
* Override mechanisms
* Approval thresholds
* Read-only vs intervention modes
* Emergency stop procedures

---

## **8️⃣ UI / OBSERVABILITY**

Design a UI that shows:

* Live positions
* Strategy rationales
* Confidence scores
* Risk metrics
* Agent decisions & disagreements
* Audit logs
* Replay of decision timelines

---

## **9️⃣ SECURITY & SAFETY**

Include:

* Permission boundaries
* Key management
* Blast-radius containment
* Rate limiting
* Compliance hooks
* Explainability requirements

---

## **🔟 FINAL OUTPUT FORMAT**

Your final answer **must include**:

1. A **clear, structured explanation**
2. A **full ASCII system diagram**
3. A **table of agents & responsibilities**
4. A **step-by-step trade lifecycle walkthrough**
5. Design decisions & tradeoffs

Be explicit, technical, and assume this system is being reviewed by senior engineers, quants, and risk officers.

---

## 🧠 THINKING STYLE

* Be rigorous, not vague
* Prefer explicit over implicit
* Prefer modular over monolithic
* Prefer safety over raw performance
* Prefer explainability over opacity

---

## 🧩 SYSTEM ARCHITECTURE DIAGRAM (ASCII)

```
┌──────────────────────────────────────────────┐
│              HUMAN OPERATOR (HITL)            │
│   UI / Override / Approval / Kill Switch      │
└───────────────▲──────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│            GOVERNOR / ORCHESTRATOR             │
│  - Scheduling                                 │
│  - Permissions                                │
│  - Capital Allocation                         │
│  - Global Constraints                         │
└───────────────▲──────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│            MARKET DATA LAYER                   │
│  Price Feeds | Order Books | On-chain | News  │
└───────────────▲──────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│         FEATURE ENGINEERING AGENTS             │
│  Indicators | Regimes | Volatility | Factors  │
└───────────────▲──────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│             STRATEGY AGENT POOL                │
│  Trend | Mean Reversion | Breakout | ML | etc │
└───────────────▲──────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│        CONSENSUS / SIGNAL AGGREGATOR           │
│  Voting | Confidence Weighting | Conflict Res │
└───────────────▲──────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│           RISK MANAGEMENT AGENTS               │
│  Exposure | Drawdown | Volatility | Limits    │
└───────────────▲──────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│         VERIFICATION & QA AGENTS               │
│  Sanity Checks | Backtest Compare | Anomaly   │
└───────────────▲──────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│          TRADE CONSTRUCTION AGENT              │
│  Position Size | Stops | Targets | Timing     │
└───────────────▲──────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│            EXECUTION AGENT                     │
│  Smart Routing | Slippage | Retry | Rollback  │
└───────────────▲──────────────────────────────┘
                │
┌───────────────┴──────────────────────────────┐
│         MONITORING & AUDIT AGENTS              │
│  Logs | Metrics | Alerts | Post-Trade Review  │
└──────────────────────────────────────────────┘
```

---

## 🧠 WHY THIS PROMPT IS “MAXED OUT”

This prompt:

* Eliminates ambiguity
* Forces modular thinking
* Prevents unsafe shortcuts
* Encourages explainable AI
* Aligns with real-world trading constraints
* Is compatible with LangGraph, smolagents, custom DAGs, or Antigravity

If you want, next I can:

* Convert this into a **LangGraph graph**
* Generate **agent-specific system prompts**
* Design the **UI wireframe**
* Add **regulatory/compliance layers**
* Or **downgrade this to a lean MVP version**

Just tell me the next move.
