# Tasks


I want the architecture to be structured in the following manner:

The governor creates Market Data agents.

The market data agents fetch market data for each of the timeframes: 1w, 1d, 4h, 1h, 30m, 15m and 5m.

The market data agent then calculates indicators on this dataframe and stores them in columns in the dataframe. The indicators are already mostly calculated.

the market data agent then adds the market data along with its indicators to an object that will store ALL the information about a certain symbol. This object is referred to in the documentation as the "analysis" object, but I suggest you come up with the best name possible for it. The schema for this object is defined in app/models/analysis.json, and it contains plenty of data and information. Essentially it will hold all the information associated with a certain symbol, and it will be used ultimately to make decisions on trading.

Each agent will have access to this analysis object, and read and write values to it for different purposes. Specific agents will be tasked with populating certain pieces of information for this object in order to create a complete picture of the symbol.

the market data agent will populate the analysis object with the following fields:

- market_data.1w = pandas DataFrame with fetched data for 1w timeframe and all the indicators calculated on it.
- market_data.1d = pandas DataFrame with fetched data for 1d timeframe and all the indicators calculated on it.
- market_data.4h = pandas DataFrame with fetched data for 4h timeframe and all the indicators calculated on it.
- market_data.1h = pandas DataFrame with fetched data for 1h timeframe and all the indicators calculated on it.
- market_data.30m = pandas DataFrame with fetched data for 30m timeframe and all the indicators calculated on it.
- market_data.15m = pandas DataFrame with fetched data for 15m timeframe and all the indicators calculated on it.
- market_data.5m = pandas DataFrame with fetched data for 5m timeframe and all the indicators calculated on it.
- symbol = symbol name (e.g. BTC-USDT)
- date_created = date and time the analysis object was created, as a unix timestamp
- analysis_state = "IN_PROGRESS"
- market_structure.adx: TRENDING or NEUTRAL based on whether the latest adx value is greater or equal to 23.
- market_structure.last_updated = date and time the market structure was last updated (current time), as a unix timestamp

Once all timeframes have been fetched, the Key Levels Agent is tasked with populating the analysis object with the following fields:

- key_levels.daily_open: today's open price
- key_levels.weekly_open: this week's open price
- key_levels.monthly_open: this month's open price
- key_levels.previous_day_high: yesterday's highest price
- key_levels.previous_day_low: yesterday's lowest price
- key_levels.previous_month_high: last month's highest price
- key_levels.previous_month_low: last month's lowest price
- key_levels.last_updated = date and time the key levels were last updated (current time), as a unix timestamp









Below is a **fully rewritten, maximally prompt-engineered version** of your prompt, designed specifically for an **AI Coder Agent** (like AntiGravity).
It uses best practices for:

* Role clarity
* Explicit objectives
* Architectural constraints
* Data contracts
* Event-driven behavior
* Incremental scope control
* Acceptance criteria
* Assumptions & non-goals

You can copy-paste this directly as the **system or primary task prompt** for the agent.

---

# 🔧 AntiGravity AI Coder Agent — Core Architecture Task

## Role Definition

You are **AntiGravity**, an expert AI software engineer specializing in:

* Event-driven systems
* Multi-agent architectures
* Financial market data pipelines
* Shared-state concurrency safety
* Python-based data engineering
* LangChain + local LLM integration (Ollama)

Your task is to **design and implement a robust, shared analysis object architecture** and update existing agents to use it correctly.

---

## High-Level Objective

Design and implement a **symbol-scoped Analysis Object** that:

1. Acts as the **single source of truth** for all data related to a trading symbol
2. Is **shared across multiple autonomous agents**
3. Supports **concurrent reads and writes without conflicts**
4. Ensures **agents always read the latest state**
5. Is **event-driven**, so agents react to updates instead of polling
6. Strictly follows the JSON schema defined in:

```
app/models/analysis.json
```

---

## Core Architectural Requirements

### 1. Analysis Object (Critical)

* There must be **exactly one analysis object per symbol**
* All symbol-related data MUST live inside this object
* The object MUST conform to `analysis.json`
* This object is:

  * Read by all agents
  * Written by multiple agents
  * Updated incrementally (never overwritten wholesale)

### Required Properties

* **Versioned or timestamped updates** to prevent stale writes
* **Granular section-level updates** (agents only mutate their owned sections)
* **Thread-safe or event-safe access** (depending on architecture)
* Designed for **horizontal scalability** (more agents later)

---

## Agent Responsibilities (Future-Proofed)

Each agent:

* Knows **which section(s)** it owns
* Knows **which section(s)** it consumes
* Never mutates sections it does not own
* Emits events when it updates its section

---

## Initial Scope (IMPORTANT)

To reduce complexity, **only implement the following two agents for now**:

### ✅ Agents to Implement Now

1. **Market Data Agent**
2. **Market Structure Agent**

❌ All other agents are **out of scope for this task**
(They will be added later using the same architecture.)

---

## Agent-Specific Requirements

---

### 📈 Market Data Agent

#### Current State

* Already mostly implemented
* Produces indicator-enriched OHLCV data
* Maintains one DataFrame per timeframe

#### Required Changes

You must update it to:

1. **Write exclusively to the analysis object**
2. Populate:

   ```
   analysis.market_data[timeframe]
   ```
3. Store:

   * One DataFrame per timeframe
   * All existing indicator columns (unchanged)
4. **Publish an event** whenever market data is updated

#### Event Requirements

* Event must include:

  * symbol
  * timeframe(s) updated
  * version or timestamp
* Evaluate whether the **existing event publishing mechanism**:

  * Is sufficient
  * Needs modification for multi-agent coordination

---

### 📐 Market Structure Agent

#### Behavior

* Subscribes to **market data update events**
* Reacts per symbol + timeframe
* Reads market data from the analysis object
* Computes and updates **only** its owned section

#### Must Update the Following Fields

Inside:

```
analysis.market_structure[timeframe]
```

Set and maintain:

* `highs`
* `lows`
* `pivot_points`
* `emas`

⚠️ Do NOT duplicate market data
⚠️ Do NOT recompute indicators owned by Market Data Agent

---

## Data Ownership Rules (Non-Negotiable)

| Section          | Owning Agent           |
| ---------------- | ---------------------- |
| market_data      | Market Data Agent      |
| market_structure | Market Structure Agent |

* Agents may **read** any section
* Agents may **write only** to their owned section
* Violations are architecture bugs

---

## Concurrency & Consistency Requirements

You must design a solution that ensures:

* No lost updates
* No stale reads
* No race conditions
* Deterministic event handling

Acceptable approaches include (but are not limited to):

* Copy-on-write + versioning
* Section-level locks
* Event-sourced updates
* Immutable snapshots + diff application

Explain your chosen approach in comments or documentation.

---

## LLM Integration Constraints

* LLMs may be used **only if needed**
* Ollama is available locally on the default port
* Use **LangChain** if you integrate LLM calls
* Do NOT assume external APIs or cloud LLMs

---

## Documentation & Code Quality Requirements

* Follow clean architecture principles
* Add docstrings where non-obvious
* Clearly separate:

  * Data models
  * Event handling
  * Agent logic
* Avoid tight coupling between agents

---

## Acceptance Criteria

This task is complete when:

1. A valid, schema-compliant analysis object exists per symbol
2. Market Data Agent:

   * Writes market data into it
   * Emits update events
3. Market Structure Agent:

   * Listens to those events
   * Reads from the analysis object
   * Updates market structure fields correctly
4. No agent overwrites another agent’s data
5. Architecture clearly supports adding future agents

---

## Explicit Non-Goals (Do NOT Do These)

* Do NOT implement the other agents yet
* Do NOT redesign indicator logic
* Do NOT hardcode symbol-specific logic
* Do NOT bypass the analysis object for data sharing

---

## Final Instruction

Proceed **step by step**:

1. Design the analysis object lifecycle
2. Explain concurrency strategy briefly
3. Update Market Data Agent
4. Implement Market Structure Agent
5. Verify event flow and data consistency

Be precise. Be deterministic. Optimize for correctness and extensibility.

---

If you want, next I can:

* Tailor this prompt specifically for **Claude / GPT / Code Llama**
* Produce a **separate system + developer + task prompt split**
* Generate a **companion schema validation or test prompt**
* Write the **actual implementation plan or code skeleton**
