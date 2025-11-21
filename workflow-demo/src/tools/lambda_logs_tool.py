"""
Lambda Logs Tool - LangChain wrapper for Lambda log retrieval
"""

import json
from langchain_core.tools import tool
from .logs import LogSearchTool

@tool("get_lambda_logs")
def get_lambda_logs(function_name: str, trace_id: str = None, request_id: str = None, 
                   start_time: str = None, end_time: str = None) -> str:
    """Get logs for AWS Lambda function, optionally filtered by trace ID, request ID, or time range.
    
    Args:
        function_name: Name of the Lambda function in plaintext e.g. "serverless-app-for-aiops-GetById"
        trace_id: AWS X-Ray trace ID to filter logs (optional)
        request_id: Lambda request ID to filter logs (optional)  
        start_time: Start time in ISO format like '2023-10-01T00:00:00Z' (optional)
        end_time: End time in ISO format like '2023-10-01T23:59:59Z' (optional)
    
    Returns:
        JSON string containing log entries and analysis
    """
    try:
        log_tool = LogSearchTool()
        result = log_tool.search_logs(
            function_name=function_name,
            trace_id=trace_id,
            request_id=request_id,
            start_time=start_time,
            end_time=end_time
        )
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "error": f"Failed to retrieve Lambda logs: {str(e)}",
            "function_name": function_name,
            "trace_id": trace_id,
            "request_id": request_id
        }, indent=2)
