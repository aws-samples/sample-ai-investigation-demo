"""
Logs Collector Agent in the AIOps workflow
In the current step your role is to gather detailed logs information about the key resources either affected by the CloudWatch alert or relevant. Resource includes Lambda functions, EC2 instances, EKS services. You shall be provided with a json formatted input with 'affected_resources' and 'relevant_resources'. follow the instructions below to finish you work.

You should:
1. Collect detailed logs related to the issue - log group information can be found from the user input. e.g. if the relevant_resources contains lambda function, you can leverage "get_lambda_logs" tool for this by providing trace_id under trace_analytics->trace and lambda function name from relevant_resources. when search logs, you should search only last 10 minutes, from now to 10 minutes ago. 

example input:
{
    "trace_analysis": {
      "trace": [
            {
            "trace_id": "1-68534cb6-7cc352b809142fdf4f337baa"
            }
        ],
        "relevant_resources": [
            {
            "resource_id": "serverless-app-for-aiops-GetByIdFunctionCCE22B29-QIT0IARfGe3Y",
            "resource_type": "AWS::Lambda::Function",
            "reason": "Lambda function with insufficient S3 bucket access permissions"
            }
        ]
    }
}
In this example, trace_id can be collected under trace_analysis -> trace -> trace_id. Lambda function name can be found under trace_analysis -> relevant_resources -> resource_id. You can leverage "get_lambda_logs" tool to collect error logs


Alternatively if the "get_lambda_logs" tool does not work. you should try to find the log group name and leverage aws cli tool to get logs
e.g. aws logs filter-log-events --log-group-name /aws/lambda/serverless-app-for-aiops-GetByIdFunctionCCE22B29-QIT0IARfGe3Y --filter-pattern "1-684acd23-23534686415e3fef201e4024 OR 1-684accb6-2a248d921e3d0ed0290424ef" --start-time $(date -v-30M +%s) --end-time $(date +%s) --limit 50

2. Summarize the top 10 most relevant log entries for each resource, focusing on errors, warnings, and unusual patterns.

3. Provide a concise summary of the log analysis findings.

Your output will be passed to the CloudTrail collector agent and then to the incident processor agent.

Output MUST be strictly in JSON format with the following structure:
- log_analysis: json object with the following attributes:
    - log_data: List of log entries with the following attributes:
        - resource_name: "Name of the resource",
        - log_group_name: "Log group name",
        - logs: List of log entries with error level, only the most relevant 5 entries should be included with complete message and timestamp attributes
        - summary: "Concise summary of log analysis findings"
    - summary: "Overall summary of the log analysis findings"
}

"""

import json
import sys
import os
import boto3
import logging
from langchain_core.tools import tool
from langchain_core.messages import AIMessage

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import COMMON_TOOLS, create_prompt_template, create_agent_executor, invoke_agent_with_retry
from agents.agent import Agent
from tools.lambda_logs_tool import get_lambda_logs

class LogsCollectorAgent(Agent):
    """Logs Collector Agent for gathering detailed logs information"""
    
    def __init__(self):
        """Initialize the Logs Collector Agent"""
        super().__init__("Logs Collector Agent")
        self.prompt = create_prompt_template("Logs Collection", __doc__)
        self.agent_executor = create_agent_executor(self.model, LOGS_COLLECTOR_TOOLS, self.prompt)
    
    def process(self, input_data):
        """
        Process the input data and return logs collection results
        
        Args:
            input_data: Input data containing resource information
            
        Returns:
            Dict containing logs collection results
        """
        try:
            result = invoke_agent_with_retry(
                self.agent_executor,
                {"input": f"Collect and summarize logs information about these resources:\n\n{input_data}"},
                self.logger
            )
            
            if result:
                return result["output"]
            else:
                raise Exception("Agent execution failed after all retries")
                
        except Exception as e:
            error_msg = f"Logs collector agent execution failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            # Return a structured error response
            return json.dumps({
                "log_analysis": {
                    "log_data": [],
                    "summary": f"Logs collection failed: {error_msg}"
                },
                "error": error_msg
            }, indent=2)

# Logs collector tools
LOGS_COLLECTOR_TOOLS = COMMON_TOOLS.copy()
LOGS_COLLECTOR_TOOLS.append(get_lambda_logs)
