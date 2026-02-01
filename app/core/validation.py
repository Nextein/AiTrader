import logging
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("Validation")

def validate_llm_response(data: Any, required_keys: List[str], agent_name: str = "UnknownAgent") -> bool:
    """
    Enhanced validation for LLM JSON output with verbose error reporting.
    """
    if not isinstance(data, dict):
        data_preview = str(data)[:500] if data else "None"
        logger.error(
            f"\n{'='*60}\n"
            f"❌ LLM VALIDATION FAILURE: {agent_name}\n"
            f"{'='*60}\n"
            f"Reason: Expected a JSON dictionary but received {type(data).__name__}\n"
            f"Data Preview:\n{data_preview}\n"
            f"{'='*60}"
        )
        return False
    
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        available_keys = list(data.keys())
        logger.error(
            f"\n{'='*60}\n"
            f"❌ LLM SCHEMA MISSING KEYS: {agent_name}\n"
            f"{'='*60}\n"
            f"Missing required fields: {missing_keys}\n"
            f"\nFields Present: {available_keys}\n"
            f"Fields Expected: {required_keys}\n"
            f"\nFull Data Received:\n{data}\n"
            f"{'='*60}"
        )
        return False
    
    logger.debug(f"✅ [{agent_name}] LLM output validation passed: {list(data.keys())}")
    return True

async def safe_transfer(analysis, section: str, data: Dict[str, Any], timeframe: str = None):
    """
    Safely transfers data to the analysis object if not empty.
    """
    if not data:
        logger.warning(f"Safe transfer aborted: No data to transfer for {section}")
        return False
    
    try:
        await analysis.update_section(section, data, timeframe)
        return True
    except Exception as e:
        logger.error(f"Error during safe transfer to {section}: {e}")
        return False
