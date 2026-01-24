# AI Trader Agent Architecture

This document describes the multi-agent architecture and event-driven workflow of the AI Trader application.

## High-Level Workflow

The system operates as a **Hierarchical Multi-Agent System** connected via an asynchronous **Event Bus**. This design ensures loose coupling, fault tolerance, and specialized reasoning for different trading tasks.

### Mermaid Flowchart

```mermaid
graph TD
    subgraph L0_Orchestration [L0: Orchestration]
        Governor[Governor Agent]
    end

    subgraph L1_Data [L1: Data Layer]
        MarketData[Market Data Agent]
    end

    subgraph L2_Analysis [L2: Analysis Layer]
        Regime[Regime Detection Agent]
        Anomaly[Anomaly Detection Agent]
    end

    subgraph L3_Signals [L3: Signal Generation]
        Strategy1[RSI/MACD Strategy Agent]
        Strategy2[EMA Cross Strategy Agent]
    end

    subgraph L4_Consensus [L4: Consensus Layer]
        Aggregator[Aggregator Agent]
    end

    subgraph L5_Control [L5: Risk & Control]
        Risk[Risk Agent]
    end

    subgraph L8_Execution [L8: Execution Layer]
        Execution[Execution Agent]
    end

    subgraph L9_Observability [L9: Observability]
        Audit[Audit Log Agent]
    end

    %% Initialization
    Governor -- "Starts/Stops" --> MarketData
    Governor -- "Starts/Stops" --> Strategy1
    Governor -- "Starts/Stops" --> Strategy2
    Governor -- "Starts/Stops" --> Aggregator
    Governor -- "Starts/Stops" --> Risk
    Governor -- "Starts/Stops" --> Execution
    Governor -- "Starts/Stops" --> Audit

    %% Data Flow
    MarketData -- "MARKET_DATA" --> Strategy1
    MarketData -- "MARKET_DATA" --> Strategy2
    MarketData -- "MARKET_DATA" --> Regime
    MarketData -- "MARKET_DATA" --> Anomaly

    %% Signal Flow
    Strategy1 -- "STRATEGY_SIGNAL" --> Aggregator
    Strategy2 -- "STRATEGY_SIGNAL" --> Aggregator
    Regime -- "REGIME_CHANGE" --> Aggregator

    %% Decision Flow
    Aggregator -- "SIGNAL (Consensus)" --> Risk
    Aggregator -- "SIGNAL (Consensus)" --> Anomaly
    
    %% Execution Flow
    Risk -- "ORDER_REQUEST" --> Execution
    Execution -- "ORDER_FILLED" --> Audit

    %% Monitoring Flow
    MarketData -. "ALL EVENTS" .-> Audit
    Strategy1 -.-> Audit
    Aggregator -.-> Audit
    Risk -.-> Audit
    Execution -.-> Audit
    Anomaly -- "ANOMALY_ALERT" --> Audit

    %% Style
    style Governor fill:#f9f,stroke:#333,stroke-width:2px
    style MarketData fill:#bbf,stroke:#333
    style Strategy1 fill:#bfb,stroke:#333
    style Strategy2 fill:#bfb,stroke:#333
    style Aggregator fill:#fdb,stroke:#333
    style Risk fill:#fbb,stroke:#333
    style Execution fill:#f99,stroke:#333
    style Audit fill:#ddd,stroke:#333
```

## Agent Responsibilities

| Agent | Responsibility | Key Inputs | Key Outputs |
| :--- | :--- | :--- | :--- |
| [**Governor**](./agents/governor_agent.md) | Orchestrates the system lifecycle and manages agent state. | System Config | Start/Stop Commands |
| [**Market Data**](./agents/market_data_agent.md) | Fetches real-time OHLCV data from BingX and persists it. | Exchange API | `MARKET_DATA` |
| [**Strategy Agents**](./agents/strategy_agents.md) | Apply technical indicators (RSI, MACD, EMA) to generate trade ideas. | `MARKET_DATA` | `STRATEGY_SIGNAL` |
| [**Regime Detection**](./agents/regime_detection_agent.md)| Classifies the market (Trending vs Ranging) to adjust strategy weights. | `MARKET_DATA` | `REGIME_CHANGE` |
| [**Aggregator**](./agents/aggregator_agent.md) | Buffers signals and finds consensus using regime-adaptive weighting. | `STRATEGY_SIGNAL` | `SIGNAL` (Consensus) |
| [**Risk Agent**](./agents/risk_agent.md) | Validates account balance, calculates position sizing, and enforces limits. | `SIGNAL` | `ORDER_REQUEST` |
| [**Execution**](./agents/execution_agent.md) | Handles the low-level API interaction to place orders on the exchange. | `ORDER_REQUEST` | `ORDER_FILLED` |
| [**Anomaly Detection**](./agents/anomaly_detection_agent.md)| Monitors for flash crashes or excessive system signal frequency. | `MARKET_DATA`, `SIGNAL`| `ANOMALY_ALERT` |
| [**Audit Log**](./agents/audit_log_agent.md) | Listens to all bus traffic and creates a permanent record in the database. | All Event Types | Database Records |

## Implementation Details

- **Event Bus**: An asynchronous pub-sub mechanism (`app/core/event_bus.py`) that decouples agents.
- **Base Agent**: All agents inherit from `BaseAgent`, providing a standardized `run_loop` and lifecycle management.
- **Regime-Adaptive Weighting**: The Aggregator increases EMA weights in `TRENDING` markets and RSI weights in `RANGING` markets.
- **Safety**: The Risk Agent acts as a final gateway, ensuring no trade is placed without sufficient liquidity and confidence.
