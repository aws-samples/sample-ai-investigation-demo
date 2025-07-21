"""
Resource Collector Agent - Second agent in the AIOps workflow

Responsible for:
1. Collecting comprehensive information about directly affected resources identified by the domain bot
2. Discovering and gathering data on related resources based on resource groups (CloudFormation stacks, VPC, Tags)
3. Retrieving relevant CloudWatch metrics for all identified resources
4. Analyzing resource relationships and dependencies
5. Providing context about the infrastructure environment

The agent receives structured input from the domain bot containing:
1. Directly affected resources (resource ARNs, types, names)
2. Relevant resource groups (CloudFormation stacks, VPCs, tag-based groups)
3. Alarm details (metric name, threshold, current value, etc.)

The agent must retrieve detailed information about:
- The directly affected resources that triggered the alarm
- All related resources that might be impacted or contributing to the issue
- Current and historical CloudWatch metrics for relevant resources
- Resource configurations, status, and health checks
"""

import sys
import os
import json
from langchain_core.messages import AIMessage

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import get_bedrock_model, create_prompt_template, create_agent_executor, COMMON_TOOLS
from agents.agent import Agent

class ResourceCollectorAgent(Agent):
    """Resource Collector Agent for gathering resource information"""
    
    def __init__(self):
        """Initialize the Resource Collector Agent"""
        super().__init__("Resource Collector Agent")
        self.prompt = create_prompt_template("Resource Collector", __doc__)
        self.agent_executor = create_agent_executor(self.model, COMMON_TOOLS, self.prompt)
    
    def process(self, input_data):
        """
        Process the input data and return resource collection results
        
        Args:
            input_data: Input data containing resource information
            
        Returns:
            Dict containing resource collection results
        """
        result = self.agent_executor.invoke({
            "input": f"Collect information about these resources:\n\n{input_data}"
        })
        
        return result["output"]
