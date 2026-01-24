# Task prompt

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







# Agent output



Summary of Changes
1. Core Architecture: 
app/core/analysis.py
Implemented 
AnalysisObject
, a thread-safe (using asyncio.Lock) container for all symbol-related data.
It conforms to the 
app/models/analysis.json
 schema and supports incremental updates to specific sections (e.g., 
market_data
, 
market_structure
).
Implemented 
AnalysisManager
 to manage these objects on a per-symbol basis, ensuring a single source of truth for each symbol.
2. Market Data Agent: 
app/agents/market_data_agent.py
Updated the agent to write its indicator-enriched DataFrames directly to the 
AnalysisObject
 under the 
market_data
 section.
Reduced the event payload size for EventType.MARKET_DATA to include only metadata (symbol, timeframe, timestamp), encouraging other agents to read the heavy data directly from the shared 
AnalysisObject
.
Ensured it populates 
symbol
, date_created, and sets analysis_state to IN_PROGRESS.
3. Market Structure Agent: 
app/agents/market_structure_agent.py
 (New)
Created a new event-driven agent that subscribes to 
market_data
 updates.
It reads the latest DataFrame from the shared 
AnalysisObject
, calculates the market structure state, and updates the 
market_structure
 section.
Fields Updated:
highs: HIGHER or LOWER based on candle high comparison.
lows: HIGHER or LOWER based on candle low comparison.
pivot_points: UP or DOWN based on pivot direction.
emas: UP or DOWN based on EMA 21 trend.
adx: TRENDING or NEUTRAL based on whether the ADX value is $\ge 23$.
last_updated: ISO timestamp and Unix timestamp as requested.
4. Configuration & Orchestration
app/core/config.py
: Added TIMEFRAMES list to settings to support multi-timeframe fetching.
app/agents/governor_agent.py
: Updated to include 
MarketStructureAgent
 and temporarily narrowed the active agents to only 
MarketDataAgent
 and 
MarketStructureAgent
 to follow the initial scope requirements.
Verification Results
I ran a verification script (
verify_analysis.py
) which confirmed:

MarketDataAgent
 correctly fetches and stores DataFrames in the shared object.
MarketStructureAgent
 successfully reacts to events, reads the shared data, and populates the market structure analysis fields for multiple timeframes (e.g., 4h, 1h).
The architecture supports concurrent updates without data loss.




Walkthrough - Symbol Discovery and Sanity Check
I have completed the tasks in 
TODO.md
 regarding symbol discovery, filtering, and sanity checking.

Changes Made
1. Configuration Update
Modified 
config.py
 to include settings for Ollama:

OLLAMA_BASE_URL: http://localhost:11434
OLLAMA_MODEL: phi3:mini
2. Sanity Agent Implementation
Created 
sanity_agent.py
:

Uses LangChain with Ollama to validate symbols.
Implements a strict prompt to filter out leveraged tokens (BTCUP), multipliers (1000PEPE), and other "weird" assets.
3. Governor Agent Integration
Updated 
governor_agent.py
:

Implemented 
initialize_symbols_task
 which:
Fetches all USDT perpetual contracts from BingX.
Prioritizes the Top 10 symbols.
Randomizes the rest of the symbols.
Calls 
SanityAgent
 for each symbol.
Publishes a SYMBOL_APPROVED event for valid coins.
4. Market Data Agent Update
Updated 
market_data_agent.py
:

Now listens for SYMBOL_APPROVED events.
Dynamically adds approved symbols to its fetch loop.
Ensures 
AnalysisObject
 is only created for approved symbols.
Verification Results
Sanity Agent Testing
I ran a test script 
verify_sanity.py
 which confirmed the following:

PASSED: BTC-USDT, ETH-USDT, SOL-USDT, LTC-USDT
REJECTED: BTCUP-USDT, BTCDOWN-USDT, 1000PEPE-USDT, 1000SHIB-USDT
Governor Integration Testing
I ran 
verify_governor_init.py
 which demonstrated the full flow:

Found ~300+ potential symbols on BingX.
Successfully approved major coins like BTC, ETH, LINK, BCH, ADA.
Correctly skipped derivative or unknown assets.
# First 5 approved in test:
['BTC/USDT:USDT', 'ETH/USDT:USDT', 'LINK/USDT:USDT', 'BCH/USDT:USDT', 'ADA/USDT:USDT']
The system now automatically discovers the best symbols to trade while filtering out trash!


The list of symbols should not be predefined. Instead, it should be fetched from the exchange. Then, the symbols should be filtered to only include USDT perpetual contracts, if they are not filtered already (I believe there is an API endpoint only for USDT perpetual contracts, but I might be wrong).

The top 10 symbols should be analysed first, and then the rest should be analysed in a random order.

The first thing that should happen for each symbol is a check to see whether the symbol is an actual cryptocurrency coin or token or if it's some weird derivative like BTCUP-USDT or 1000PEPE-USDT or something similar.

To do so, the Governor Agent should call the Sanity Agent with the symbol as a parameter. The Sanity Agent should return a boolean value indicating whether the symbol is a valid cryptocurrency coin or token or not. To do so it should simply ask the LLM via langchain if the symbol is a valid cryptocurrency coin or token or not. This question should be wrapped in a prompt with maxed out prompt engineering and best practices to ensure a correct answer every time. The LLM available is running locally on ollama. It is phi3:mini, and it is available on my windows laptop via ollama in the usual port.

Only if the Sanity Agent returns true should the analysis object for that symbol be created. If it returns false, the symbol should be skipped.