import logging
from typing import Dict, Any, List, Optional, Type
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("Validation")

def validate_llm_response(data: Any, required_keys: List[str], agent_name: str = "UnknownAgent") -> bool:
    """
    Simple validation for LLM JSON output.
    Checks if data is a dict and has all required keys.
    """
    if not isinstance(data, dict):
        logger.error(f"[{agent_name}] Validation failed: Output is {type(data)}, expected dict. Data: {data}")
        return False
    
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        logger.error(f"[{agent_name}] Validation failed: Missing keys {missing_keys}")
        return False
    
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
