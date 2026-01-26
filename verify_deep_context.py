import os
import sys
import pandas as pd
import numpy as np
import json

# Add the app directory to sys.path
sys.path.append(os.path.abspath(os.getcwd()))

from app.core.prompt_loader import PromptLoader
from app.agents.base_agent import BaseAgent

# BaseAgent is abstract, so we need a concrete implementation for testing
class MockAgent(BaseAgent):
    def __init__(self, name):
        super().__init__(name)
    async def run_loop(self):
        pass

def generate_mock_df(n=100):
    data = {
        'timestamp': pd.date_range(start='2024-01-01', periods=n, freq='h').view(np.int64) // 10**6,
        'Open': np.random.uniform(80000, 90000, n),
        'High': np.random.uniform(80000, 90000, n),
        'Low': np.random.uniform(80000, 90000, n),
        'Close': np.random.uniform(80000, 90000, n),
        'Volume': np.random.uniform(10, 100, n),
        'Exponential Moving Average 9': np.random.uniform(80000, 90000, n),
        'Exponential Moving Average 21': np.random.uniform(80000, 90000, n),
        'Exponential Moving Average 55': np.random.uniform(80000, 90000, n),
        'Linear Regression Slope': np.random.uniform(-1, 1, n),
        'Heikin Ashi Close': np.random.uniform(80000, 90000, n),
        'Relative Candles Phase': np.random.choice([1, -1], n),
        'Average Directional Index': np.random.uniform(10, 50, n),
        'Weis Waves Volume': np.random.uniform(100, 1000, n),
        'Weis Waves Direction': np.random.choice([1, -1], n)
    }
    return pd.DataFrame(data)

def verify_deep_context():
    base = MockAgent("Verifier")
    df = generate_mock_df(100)
    
    # Common analysis parts
    analysis_summary = {
        "price": 88000.0,
        "market_structure": {"highs": "HIGHER", "lows": "HIGHER", "emas_in_order": "ASCENDING"},
        "regime": "BULLISH",
        "overall_regime": "BULLISH",
        "value_areas": {"vah": 88500, "val": 87500, "poc": 88000}
    }

    test_cases = [
        ("strategies", "ema_strategy", ['Open', 'High', 'Low', 'Close', 'Exponential Moving Average 9', 'Exponential Moving Average 21', 'Exponential Moving Average 55']),
        ("strategies", "sfp_strategy", ['Open', 'High', 'Low', 'Close', 'Volume', 'Weis Waves Volume', 'Weis Waves Direction']),
        ("strategies", "bounce_strategy", ['Open', 'High', 'Low', 'Close', 'Exponential Moving Average 21', 'Linear Regression Slope']),
        ("strategies", "cycles_strategy", ['Open', 'High', 'Low', 'Close', 'Heikin Ashi Close', 'Relative Candles Phase']),
        ("market_structure", "ema_analysis", ['Open', 'High', 'Low', 'Close', 'Exponential Moving Average 9', 'Exponential Moving Average 21', 'Exponential Moving Average 55']),
        ("regime_detection", "regime_decision", ['Open', 'High', 'Low', 'Close', 'Volume', 'Average Directional Index', 'Relative Candles Phase']),
        ("analyst", "top_down_analysis", None) # Analyst is special
    ]

    for agent, task, cols in test_cases:
        print(f"--- Verifying {agent}/{task} ---")
        try:
            template = PromptLoader.load(agent, task)
            
            if agent == "analyst":
                h4_context = base.format_market_context(df, window=20)
                h1_context = base.format_market_context(df, window=20)
                combined_context = f"### 4H Context\n{h4_context}\n\n### 1H Context\n{h1_context}"
                context = {
                    "symbol": "BTC-USDT",
                    "timeframe": "1h",
                    "market_context": combined_context,
                    "analysis_summary": analysis_summary
                }
            else:
                context = {
                    "symbol": "BTC-USDT",
                    "timeframe": "1h",
                    "market_context": base.format_market_context(df, window=20, columns=cols),
                    "analysis_summary": analysis_summary
                }
            
            # Format and check
            messages = template.format_messages(**context)
            # Print a snippet of the user message (which contains the table)
            user_msg = [m.content for m in messages if m.type == 'human'][0]
            print(f"  [OK] Successfully formatted. Snippet:\n{user_msg[:200]}...")
            
        except Exception as e:
            print(f"  [ERROR] Failed: {e}")
        print("\n")

if __name__ == "__main__":
    verify_deep_context()
