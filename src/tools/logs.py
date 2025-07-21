import json
import time
import boto3
import re
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
from datetime import datetime, timedelta

def extract_request_id(log_message: str) -> Optional[str]:
    """Extract the request ID from a Lambda log message.
    
    Args:
        log_message (str): The log message to extract the request ID from.
        
    Returns:
        Optional[str]: The extracted request ID, or None if not found.
    """
    # Pattern for "RequestId: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    request_id_pattern = r"RequestId: ([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    match = re.search(request_id_pattern, log_message)
    if match:
        return match.group(1)
    return None

def get_lambda_function_logs(function_name: str, start_time: Optional[str] = None, end_time: Optional[str] = None, 
                            trace_id: Optional[str] = None, request_id: Optional[str] = None) -> str:
    """Get logs for a specific AWS Lambda function within an optional time range.
    
    Args:
        function_name (str): The name of the Lambda function.
        start_time (Optional[str]): Start time in ISO 8601 format (e.g., '2023-10-01T00:00:00Z').
        end_time (Optional[str]): End time in ISO 8601 format (e.g., '2023-10-01T23:59:59Z').
        trace_id (Optional[str]): AWS X-Ray trace ID to filter logs.
        request_id (Optional[str]): Lambda request ID to filter logs.
        
    Returns:
        str: Logs for the specified Lambda function.
    """
    logs_client = boto3.client('logs')
    
    log_group_name = f"/aws/lambda/{function_name}"
    
    # First, check if the log group exists
    try:
        logs_client.describe_log_groups(logGroupNamePrefix=log_group_name)
    except Exception as e:
        return f"Error: Log group {log_group_name} not found. {str(e)}"
    
    # Calculate timestamps
    if start_time and end_time:
        try:
            start_timestamp = int(pd.Timestamp(start_time).timestamp())
            end_timestamp = int(pd.Timestamp(end_time).timestamp())
        except Exception as e:
            return f"Error parsing timestamps: {str(e)}"
    else:
        # Default to last 24 hours instead of just 1 hour
        end_timestamp = int(datetime.now().timestamp())
        start_timestamp = end_timestamp - (24 * 3600)  # 24 hours
    
    print(f"Searching logs from {datetime.fromtimestamp(start_timestamp)} to {datetime.fromtimestamp(end_timestamp)}")
    
    # Try two approaches: CloudWatch Logs Insights query and direct log events filtering
    
    # Approach 1: CloudWatch Logs Insights query
    try:
        # Base query
        query = "fields @timestamp, @message"
        
        # Add filters if provided
        filters = []
        if trace_id:
            filters.append(f"@message like '{trace_id}'")
        if request_id:
            filters.append(f"@message like '{request_id}'")
        
        if filters:
            query += " | filter " + " or ".join(filters)
        
        # Complete the query
        query += " | sort @timestamp desc | limit 100"
        
        print(f"Executing query: {query}")
        
        start_query_response = logs_client.start_query(
            logGroupName=log_group_name,
            startTime=start_timestamp,
            endTime=end_timestamp,
            queryString=query,
        )
        
        query_id = start_query_response['queryId']
        
        # Wait for the query to complete
        response = None
        max_attempts = 10
        attempts = 0
        
        while (response is None or response['status'] == 'Running') and attempts < max_attempts:
            print(f"Waiting for query to complete... (attempt {attempts+1}/{max_attempts})")
            response = logs_client.get_query_results(queryId=query_id)
            attempts += 1
        
        if response and response['results']:
            # Format the results for better readability
            formatted_results = []
            request_ids = set()
            
            for result in response['results']:
                result_dict = {}
                for field in result:
                    result_dict[field['field']] = field['value']
                
                # Extract request ID if present
                if '@message' in result_dict:
                    extracted_request_id = extract_request_id(result_dict['@message'])
                    if extracted_request_id:
                        result_dict['request_id'] = extracted_request_id
                        request_ids.add(extracted_request_id)
                
                formatted_results.append(result_dict)
            
            # If we found request IDs and weren't already searching by request ID,
            # search for additional logs with those request IDs
            if request_ids and not request_id:
                print(f"Found {len(request_ids)} request IDs, searching for related logs...")
                for req_id in request_ids:
                    additional_query = f"fields @timestamp, @message | filter @message like '{req_id}' | sort @timestamp asc"
                    
                    start_query_response = logs_client.start_query(
                        logGroupName=log_group_name,
                        startTime=start_timestamp,
                        endTime=end_timestamp,
                        queryString=additional_query,
                    )
                    
                    query_id = start_query_response['queryId']
                    
                    # Wait for the query to complete
                    response = None
                    attempts = 0
                    
                    while (response is None or response['status'] == 'Running') and attempts < max_attempts:
                        print(f"Waiting for request ID query to complete... (attempt {attempts+1}/{max_attempts})")
                        response = logs_client.get_query_results(queryId=query_id)
                        attempts += 1
                    
                    if response and response['results']:
                        for result in response['results']:
                            result_dict = {}
                            for field in result:
                                result_dict[field['field']] = field['value']
                            
                            # Add request ID to the result
                            result_dict['request_id'] = req_id
                            
                            # Check if this is a duplicate entry
                            is_duplicate = False
                            for existing in formatted_results:
                                if existing.get('@message') == result_dict.get('@message') and \
                                   existing.get('@timestamp') == result_dict.get('@timestamp'):
                                    is_duplicate = True
                                    break
                            
                            if not is_duplicate:
                                formatted_results.append(result_dict)
            
            # Sort results by timestamp
            formatted_results.sort(key=lambda x: x.get('@timestamp', ''), reverse=True)
            
            return json.dumps(formatted_results, indent=2)
        else:
            print("No results from CloudWatch Logs Insights query, trying direct log events approach...")
    except Exception as e:
        print(f"Error with CloudWatch Logs Insights query: {str(e)}")
    
    # Approach 2: Direct log events filtering
    try:
        all_events = []
        next_token = None
        request_ids = set()
        
        # Paginate through log events
        while True:
            filter_kwargs = {
                'logGroupName': log_group_name,
                'startTime': start_timestamp * 1000,  # Convert to milliseconds
                'endTime': end_timestamp * 1000,      # Convert to milliseconds
                'limit': 100
            }
            
            # Add filter patterns
            filter_pattern = ""
            if trace_id:
                filter_pattern += f" {trace_id}"
            if request_id:
                filter_pattern += f" {request_id}"
            
            if filter_pattern:
                filter_kwargs['filterPattern'] = filter_pattern
            
            if next_token:
                filter_kwargs['nextToken'] = next_token
            
            response = logs_client.filter_log_events(**filter_kwargs)
            
            # Process events
            for event in response.get('events', []):
                message = event.get('message', '')
                
                # Extract request ID if present
                extracted_request_id = extract_request_id(message)
                if extracted_request_id:
                    request_ids.add(extracted_request_id)
                
                all_events.append(event)
            
            # Check if there are more results
            next_token = response.get('nextToken')
            if not next_token or len(all_events) >= 100:
                break
        
        # If we found request IDs and weren't already searching by request ID,
        # search for additional logs with those request IDs
        if request_ids and not request_id:
            print(f"Found {len(request_ids)} request IDs, searching for related logs...")
            for req_id in request_ids:
                next_token = None
                while True:
                    filter_kwargs = {
                        'logGroupName': log_group_name,
                        'startTime': start_timestamp * 1000,
                        'endTime': end_timestamp * 1000,
                        'filterPattern': req_id,
                        'limit': 100
                    }
                    
                    if next_token:
                        filter_kwargs['nextToken'] = next_token
                    
                    response = logs_client.filter_log_events(**filter_kwargs)
                    
                    # Check for duplicates before adding
                    for event in response.get('events', []):
                        is_duplicate = False
                        for existing in all_events:
                            if existing['eventId'] == event['eventId']:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            all_events.append(event)
                    
                    next_token = response.get('nextToken')
                    if not next_token or len(all_events) >= 200:
                        break
        
        # Format the results
        formatted_results = []
        for event in all_events:
            message = event.get('message', '')
            result_dict = {
                '@timestamp': datetime.fromtimestamp(event['timestamp'] / 1000).isoformat(),
                '@message': message,
                'logStreamName': event['logStreamName']
            }
            
            # Extract request ID if present
            extracted_request_id = extract_request_id(message)
            if extracted_request_id:
                result_dict['request_id'] = extracted_request_id
            
            formatted_results.append(result_dict)
        
        # Sort results by timestamp
        formatted_results.sort(key=lambda x: x.get('@timestamp', ''), reverse=True)
        
        if formatted_results:
            return json.dumps(formatted_results, indent=2)
        else:
            return json.dumps([], indent=2)
    
    except Exception as e:
        return f"Error retrieving logs: {str(e)}"

class LogSearchTool:
    """Agent tool for searching Lambda function logs with trace ID."""
    
    def __init__(self):
        self.name = "log_search_tool"
        self.description = "Search AWS Lambda function logs by function name and trace ID"
    
    def search_logs(self, function_name: str, trace_id: Optional[str] = None, 
                   start_time: Optional[str] = None, end_time: Optional[str] = None,
                   request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Search logs for a specific Lambda function with optional trace ID filtering.
        
        Args:
            function_name (str): Name of the Lambda function
            trace_id (Optional[str]): AWS X-Ray trace ID to filter logs
            start_time (Optional[str]): Start time in ISO 8601 format
            end_time (Optional[str]): End time in ISO 8601 format
            request_id (Optional[str]): Lambda request ID to filter logs
            
        Returns:
            Dict[str, Any]: Search results and metadata
        """
        try:
            logs = get_lambda_function_logs(
                function_name=function_name,
                start_time=start_time,
                end_time=end_time,
                trace_id=trace_id,
                request_id=request_id
            )
            
            # Check if logs is a string that starts with "Error"
            if isinstance(logs, str) and logs.startswith("Error"):
                return {
                    "status": "error",
                    "message": logs,
                    "function_name": function_name,
                    "trace_id": trace_id,
                    "request_id": request_id
                }
            
            # Parse logs and extract request IDs if not already provided
            log_data = json.loads(logs) if logs else []
            request_ids = set()
            
            for log_entry in log_data:
                if 'request_id' in log_entry:
                    request_ids.add(log_entry['request_id'])
            
            return {
                "status": "success",
                "function_name": function_name,
                "trace_id": trace_id,
                "request_id": request_id,
                "found_request_ids": list(request_ids),
                "time_range": f"{start_time or 'last 24 hours'} to {end_time or 'now'}",
                "logs": log_data
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "function_name": function_name,
                "trace_id": trace_id,
                "request_id": request_id
            }
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the schema for this tool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "Name of the Lambda function to search logs for"
                    },
                    "trace_id": {
                        "type": "string",
                        "description": "AWS X-Ray trace ID to filter logs"
                    },
                    "request_id": {
                        "type": "string",
                        "description": "Lambda request ID to filter logs"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in ISO 8601 format (e.g., '2023-10-01T00:00:00Z')"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in ISO 8601 format (e.g., '2023-10-01T23:59:59Z')"
                    }
                },
                "required": ["function_name"]
            }
        }

# Example usage
if __name__ == "__main__":
    # Create the tool
    log_tool = LogSearchTool()
    
    # Example search by trace ID
    result = log_tool.search_logs(
        function_name="serverless-app-for-aiops-GetByIdFunctionCCE22B29-QIT0IARfGe3Y",
        trace_id="1-684c4904-47bb4c2618a189a1325a6c54"
    )
    
    print(json.dumps(result, indent=2))
