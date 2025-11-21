"""
Domain Bot Agent - First agent in the AIOps workflow

Responsible for:
1. Parsing CloudWatch alerts and identifying affected resources with high precision
2. Collecting information and identifying relevant resource groups (e.g., CloudFormation stack ID, Tags, VPC ID)
3. Extracting detailed alarm information including metrics, thresholds, and current values
4. Determining the severity and potential impact of the alert
5. Providing context for the next agent (resource collector) to list all relevant resources

Resource relationships can be identified through:
1. Resources created under the same CloudFormation stack
2. Resources within the same VPC
3. Resources sharing the same meaningful tags (e.g., application, environment, service)
4. Resources that are part of the same logical service or application

Response output MUST be strictly in JSON format with the following structure:
{
    "affected_resources": [
        {
            "resource_id": "i-0123456789abcdef0",
            "resource_type": "AWS::EC2::Instance",
            "resource_name": "web-server-1"
        }
    ],
    "resource_groups": [
        {
            "group_type": "CloudFormation Stack",
            "group_id": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack/1234abcd-5678-90ef-ab12-cd34ef56gh78"
        },
        {
            "group_type": "VPC",
            "group_id": "vpc-0123456789abcdef0"
        },
        {
            "group_type": "Tags",
            "group_id": "Application=MyApp,Environment=Production"
        }
    ],
    "alarm_details": {
        "alarm_name": "High CPU Utilization",
        "metric_name": "CPUUtilization",
        "namespace": "AWS/EC2",
        "threshold": 80,
        "current_value": 95.5,
        "evaluation_periods": 3,
        "period": 300,
        "statistic": "Average"
    },
    "severity": "High",
    "potential_impact": "Performance degradation for web application users",
    "related_services": ["EC2", "ELB", "RDS"]
}
"""

import sys
import os
import json
from langchain_core.messages import AIMessage

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import get_bedrock_model, create_prompt_template, create_agent_executor, COMMON_TOOLS
from agents.agent import Agent

class DomainBotAgent(Agent):
    """Domain Bot Agent for analyzing CloudWatch alerts"""
    
    def __init__(self):
        """Initialize the Domain Bot Agent"""
        super().__init__("Domain Bot Agent")
        self.prompt = create_prompt_template("Domain Bot", __doc__)
        self.agent_executor = create_agent_executor(self.model, COMMON_TOOLS, self.prompt)
    
    def process(self, input_data):
        """
        Process the input data and return domain analysis
        
        Args:
            input_data: Input data containing CloudWatch alert information
            
        Returns:
            Dict containing domain analysis results
        """
        result = self.agent_executor.invoke({
            "input": f"Analyze this CloudWatch alert and identify affected resources:\n\n{input_data}"
        })
        
        return result["output"]
