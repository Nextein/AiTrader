import os
import sys

# Add the app directory to sys.path
sys.path.append(os.path.abspath(os.getcwd()))

from app.core.prompt_loader import PromptLoader

def verify_prompts():
    prompts = [
        ("strategies", "ema_strategy"),
        ("strategies", "sfp_strategy"),
        ("strategies", "bounce_strategy"),
        ("strategies", "cycles_strategy"),
        ("market_structure", "ema_analysis"),
        ("regime_detection", "regime_decision"),
        ("analyst", "top_down_analysis"),
        ("sanity", "symbol_verify")
    ]
    
    dummy_context = {
        "symbol": "BTC-USDT",
        "timeframe": "1h",
        "price": 88000.0,
        "ema9": 87500.0,
        "ema21": 87000.0,
        "ema55": 86000.0,
        "high": 88500.0,
        "low": 87500.0,
        "close": 88000.0,
        "open": 87800.0,
        "vah": 88200.0,
        "val": 87200.0,
        "va_state": "ASCENDING",
        "regime": "BULLISH",
        "overall_regime": "BULLISH",
        "cross_9_21": "UP",
        "cross_21_55": "UP",
        "emas_in_order": "ASCENDING",
        "emas_fanning": "EXPANDING",
        "highs": "HIGHER",
        "lows": "HIGHER",
        "ms": {"highs": "HIGHER", "lows": "HIGHER"},
        "current_emas": {"9": 1, "21": 2, "55": 3, "144": 4, "252": 5},
        "previous_emas": {"9": 1, "21": 2, "55": 3, "144": 4, "252": 5},
        # Missing variables found in verification
        "lr_slope": 0.05,
        "macd_val": 10.0,
        "d1_trend": "BULLISH",
        "h4_pullback": "YES",
        "ha_dir": "UP",
        "rel_phase": 1,
        "trigger_activated": "YES",
        "h1_regime": "BULLISH",
        "atr": 500.0,
        "data": "Sample data bit",
        "obv_divergence_15m": "NONE",
        "timeframe_data": "Sample TF data"
    }
    
    for agent, task in prompts:
        print(f"Verifying {agent}/{task}...")
        try:
            template = PromptLoader.load(agent, task)
            # Formatting check
            formatted = template.format_messages(**dummy_context)
            print(f"  [OK] Successfully formatted {agent}/{task}")
        except Exception as e:
            print(f"  [ERROR] Failed to format {agent}/{task}: {e}")

if __name__ == "__main__":
    verify_prompts()
