import os
import logging
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger("PromptLoader")

class PromptLoader:
    @staticmethod
    def load(agent_name: str, task_name: str) -> ChatPromptTemplate:
        """
        Loads system and user prompts from app/prompts/<agent_name>/<task_name>/
        Files expected: system.txt, user.txt
        """
        # Get absolute path to the app/prompts directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(os.path.dirname(current_dir), "prompts", agent_name, task_name)
        
        system_path = os.path.join(base_path, "system.txt")
        user_path = os.path.join(base_path, "user.txt")
        
        messages = []
        
        if os.path.exists(system_path):
            with open(system_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    messages.append(("system", content))
        else:
            logger.warning(f"System prompt not found at {system_path}")
            
        if os.path.exists(user_path):
            with open(user_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    messages.append(("user", content))
        else:
            logger.warning(f"User prompt not found at {user_path}")
                
        if not messages:
            logger.error(f"No prompt messages found for {agent_name}/{task_name}")
            return ChatPromptTemplate.from_messages([("system", "Default prompt (error loading)")])

        return ChatPromptTemplate.from_messages(messages)
    @staticmethod
    def get_raw(agent_name: str, task_name: str) -> dict:
        """Returns raw system and user prompt strings"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(os.path.dirname(current_dir), "prompts", agent_name, task_name)
        
        res = {"system": "", "user": ""}
        
        system_path = os.path.join(base_path, "system.txt")
        user_path = os.path.join(base_path, "user.txt")
        
        if os.path.exists(system_path):
            with open(system_path, "r", encoding="utf-8") as f:
                res["system"] = f.read().strip()
                
        if os.path.exists(user_path):
            with open(user_path, "r", encoding="utf-8") as f:
                res["user"] = f.read().strip()
                
        return res

    @staticmethod
    def list_prompts() -> list:
        """Lists all available prompts in the prompts directory"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        prompts_path = os.path.join(os.path.dirname(current_dir), "prompts")
        
        prompts = []
        if not os.path.exists(prompts_path):
            return []
            
        for agent in os.listdir(prompts_path):
            agent_path = os.path.join(prompts_path, agent)
            if os.path.isdir(agent_path):
                for task in os.listdir(agent_path):
                    task_path = os.path.join(agent_path, task)
                    if os.path.isdir(task_path):
                        prompts.append(f"{agent}/{task}")
        return prompts
