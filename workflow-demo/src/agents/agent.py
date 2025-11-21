"""
Main agent module that defines the base Agent class
"""

import sys
import os
import logging

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import create_prompt_template, get_bedrock_model, COMMON_TOOLS, create_agent_executor
from constants import AgentTypes

class Agent:
    """Base Agent class for all specialized agents"""

    def __init__(self, name):
        """Initialize the agent with a name"""
        self.name = name
        self.is_xml, self.model = get_bedrock_model(0, 20000)
        self.logger = logging.getLogger(f"{__name__}.{name.replace(' ', '')}")

# Legacy function for backward compatibility
def create_my_agent():
    """Create a generic agent for backward compatibility"""
    is_xml, model = get_bedrock_model()
    prompt = create_prompt_template("DevOps Assistant", "")
    return create_agent_executor(model, COMMON_TOOLS, prompt, AgentTypes.XML_AGENT if is_xml else AgentTypes.FUNCTION_CALL_AGENT)
