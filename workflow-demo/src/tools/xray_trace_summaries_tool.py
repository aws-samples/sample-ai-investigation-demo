"""
X-Ray Trace Summaries Tool

This tool provides functionality to retrieve AWS X-Ray trace summaries
for specified services and time ranges. It's designed to be used by agents
to get relevant traces for detailed analysis without having to use the AWS CLI directly.

Usage:
- get_xray_trace_summaries('{"service_name": "Sample API/Prod", "service_type": "AWS::ApiGateway::Stage", "minutes": 30, "region": "ap-southeast-1"}')

The region parameter is optional and defaults to the session default.
The minutes parameter is optional and defaults to 30 minutes.
"""

import boto3
import json
import time
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List, Optional, Tuple
from langchain_core.tools import tool

# Set up logging
logger = logging.getLogger(__name__)

class XRayTraceSummariesTool:
    """Tool for retrieving AWS X-Ray trace summaries"""
    
    def __init__(self, region_name: Optional[str] = None):
        """
        Initialize the X-Ray trace summaries tool
        
        Args:
            region_name: AWS region name (optional, defaults to session default)
        """
        self.region_name = region_name
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the X-Ray client"""
        try:
            if self.region_name:
                self.xray_client = boto3.client('xray', region_name=self.region_name)
            else:
                self.xray_client = boto3.client('xray')
            
            # Get the actual region being used
            self.region_name = self.xray_client.meta.region_name
            logger.info(f"Initialized X-Ray client in region: {self.region_name}")
            
        except Exception as e:
            logger.error(f"Error initializing X-Ray client: {e}")
            raise
    
    def get_trace_summaries(self, 
                           service_name: str, 
                           service_type: str, 
                           minutes: int = 15,
                           max_traces: int = 2,
                           filter_errors: bool = True,
                           start_time: Optional[datetime] = None, 
                           end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get X-Ray trace summaries for a specific service
        
        Args:
            service_name: Name of the service
            service_type: Type of the service (e.g., AWS::ApiGateway::Stage)
            minutes: Number of minutes to look back from now (default: 15)
            max_traces: Maximum number of traces to return (default: 2)
            filter_errors: Whether to filter for error/fault traces only (default: True)
            start_time: Explicit start time (optional, overrides minutes)
            end_time: Explicit end time (optional, defaults to now)
            
        Returns:
            Dict containing the trace summaries
        """
        try:
            # Set up time range
            if end_time is None:
                end_time = datetime.now()  # Use local time instead of UTC
            
            if start_time is None:
                start_time = end_time - timedelta(minutes=minutes)
            
            # Convert to Unix timestamps
            start_timestamp = int(start_time.timestamp())
            end_timestamp = int(end_time.timestamp())
            
            # Build filter expression
            filter_expression = f'service(id(name: "{service_name}", type: "{service_type}"))'
            
            if filter_errors:
                filter_expression = f'(error = true or fault = true) and {filter_expression}'
            
            logger.info(f"Getting trace summaries for {service_name} ({service_type}) from {start_time} to {end_time}")
            logger.info(f"Filter expression: {filter_expression}")
            
            # Call X-Ray API
            response = self.xray_client.get_trace_summaries(
                StartTime=start_timestamp,
                EndTime=end_timestamp,
                FilterExpression=filter_expression
            )
            
            # Process the response and limit results
            trace_summaries = self._process_trace_summaries(response, max_traces)
            
            # Get trace details for each summary
            trace_details = self._get_trace_details(trace_summaries)
            
            return {
                'service_name': service_name,
                'service_type': service_type,
                'start_time': start_timestamp,
                'end_time': end_timestamp,
                'filter_expression': filter_expression,
                'trace_summaries': trace_summaries,
                'trace_details': trace_details,
                'region': self.region_name
            }
            
        except Exception as e:
            logger.error(f"Error getting trace summaries: {e}")
            return {
                'service_name': service_name,
                'service_type': service_type,
                'error': str(e),
                'trace_summaries': [],
                'trace_details': []
            }
    
    def _process_trace_summaries(self, response: Dict[str, Any], max_traces: int) -> List[Dict[str, Any]]:
        """
        Process the raw X-Ray trace summaries response
        
        Args:
            response: Raw X-Ray API response
            max_traces: Maximum number of traces to process
            
        Returns:
            List of processed trace summaries
        """
        trace_summaries = []
        
        for summary in response.get('TraceSummaries', [])[:max_traces]:
            trace_summary = {
                'id': summary.get('Id', ''),
                'duration': summary.get('Duration', 0),
                'response_time': summary.get('ResponseTime', 0),
                'has_error': summary.get('HasError', False),
                'has_fault': summary.get('HasFault', False),
                'has_throttle': summary.get('HasThrottle', False),
                'is_partial': summary.get('IsPartial', False),
                'http': summary.get('Http', {}),
                'annotations': summary.get('Annotations', {}),
                'users': summary.get('Users', []),
                'service_ids': summary.get('ServiceIds', []),
                'start_time': summary.get('StartTime', 0),
                'end_time': summary.get('EndTime', 0),
                'entry_point': summary.get('EntryPoint', {})
            }
            
            trace_summaries.append(trace_summary)
        
        return trace_summaries
    
    def _get_trace_details(self, trace_summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get detailed trace information for each trace summary
        
        Args:
            trace_summaries: List of trace summaries
            
        Returns:
            List of trace details
        """
        trace_details = []
        
        for summary in trace_summaries:
            trace_id = summary.get('id', '')
            
            if not trace_id:
                continue
            
            try:
                # Get trace details
                response = self.xray_client.batch_get_traces(
                    TraceIds=[trace_id]
                )
                
                traces = response.get('Traces', [])
                
                if traces:
                    trace = traces[0]
                    
                    # Extract segments
                    segments = []
                    for segment_doc in trace.get('Segments', []):
                        try:
                            segment = json.loads(segment_doc.get('Document', '{}'))
                            segments.append(segment)
                        except json.JSONDecodeError:
                            continue
                    
                    # Extract errors and exceptions
                    errors = []
                    for segment in segments:
                        if 'error' in segment or 'fault' in segment:
                            cause = segment.get('cause', {})
                            if cause:
                                errors.append({
                                    'service': segment.get('name', 'unknown'),
                                    'type': cause.get('exceptions', [{}])[0].get('type', '') if cause.get('exceptions') else '',
                                    'message': cause.get('exceptions', [{}])[0].get('message', '') if cause.get('exceptions') else '',
                                    'stack': cause.get('exceptions', [{}])[0].get('stack', []) if cause.get('exceptions') else []
                                })
                    
                    trace_details.append({
                        'id': trace_id,
                        'duration': trace.get('Duration', 0),
                        'segments': segments,
                        'errors': errors
                    })
            
            except Exception as e:
                logger.error(f"Error getting trace details for {trace_id}: {e}")
                trace_details.append({
                    'id': trace_id,
                    'error': str(e)
                })
        
        return trace_details
    
    def analyze_trace_summaries(self, trace_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze trace summaries to extract key findings
        
        Args:
            trace_data: Trace data from get_trace_summaries
            
        Returns:
            Dict containing analysis results
        """
        try:
            service_name = trace_data.get('service_name', 'unknown')
            service_type = trace_data.get('service_type', 'unknown')
            trace_summaries = trace_data.get('trace_summaries', [])
            trace_details = trace_data.get('trace_details', [])
            
            if not trace_summaries:
                return {
                    "error": "No trace summaries found",
                    "trace": [],
                    "metrics": [],
                    "relevant_resources": []
                }
            
            # Process each trace
            traces = []
            for i, summary in enumerate(trace_summaries):
                trace_id = summary.get('id', '')
                start_time = summary.get('start_time', 0)
                
                # Get corresponding details
                detail = next((d for d in trace_details if d.get('id') == trace_id), {})
                
                # Extract findings
                findings = []
                
                # Check for errors
                if summary.get('has_error', False):
                    findings.append("HTTP 4XX error detected")
                if summary.get('has_fault', False):
                    findings.append("HTTP 5XX error detected")
                if summary.get('has_throttle', False):
                    findings.append("Request throttling detected")
                
                # Check for latency
                duration = float(summary.get('duration', 0))
                if duration > 1.0:  # More than 1 second
                    findings.append(f"High latency detected: {duration:.2f} seconds")
                
                # Extract HTTP status if available
                http_info = summary.get('http', {})
                if http_info:
                    status = http_info.get('response', {}).get('status', 0)
                    if status >= 400:
                        findings.append(f"HTTP {status} status code")
                
                # Extract error details
                error_details = []
                for error in detail.get('errors', []):
                    error_type = error.get('type', '')
                    error_message = error.get('message', '')
                    if error_type or error_message:
                        error_details.append(f"{error_type}: {error_message}")
                
                traces.append({
                    'trace_id': trace_id,
                    'start_time': start_time.isoformat() if isinstance(start_time, datetime) else str(start_time),
                    'findings': findings,
                    'error_details': error_details
                })
            
            # Extract metrics
            metrics = []
            
            # Count error types
            error_count = sum(1 for s in trace_summaries if s.get('has_error', False))
            fault_count = sum(1 for s in trace_summaries if s.get('has_fault', False))
            throttle_count = sum(1 for s in trace_summaries if s.get('has_throttle', False))
            
            if error_count > 0:
                metrics.append({
                    'resource_name': service_name,
                    'resource_type': service_type,
                    'metric_name': '4XX Error Count',
                    'value': error_count
                })
            
            if fault_count > 0:
                metrics.append({
                    'resource_name': service_name,
                    'resource_type': service_type,
                    'metric_name': '5XX Error Count',
                    'value': fault_count
                })
            
            if throttle_count > 0:
                metrics.append({
                    'resource_name': service_name,
                    'resource_type': service_type,
                    'metric_name': 'Throttle Count',
                    'value': throttle_count
                })
            
            # Calculate average duration
            if trace_summaries:
                avg_duration = sum(float(s.get('duration', 0)) for s in trace_summaries) / len(trace_summaries)
                metrics.append({
                    'resource_name': service_name,
                    'resource_type': service_type,
                    'metric_name': 'Average Duration',
                    'value': f"{avg_duration:.2f} seconds"
                })
            
            # Extract relevant resources
            relevant_resources = []
            
            # Add the main service
            relevant_resources.append({
                'resource_id': service_name,
                'resource_type': service_type,
                'reason': 'Primary service being analyzed'
            })
            
            # Add resources from segments
            for detail in trace_details:
                for segment in detail.get('segments', []):
                    name = segment.get('name', '')
                    type_name = segment.get('aws', {}).get('resource_type', '')
                    
                    if name and name != service_name and not any(r['resource_id'] == name for r in relevant_resources):
                        reason = 'Downstream dependency'
                        
                        # Check if this segment has errors
                        if segment.get('error', False) or segment.get('fault', False):
                            reason = 'Downstream dependency with errors'
                        
                        relevant_resources.append({
                            'resource_id': name,
                            'resource_type': type_name or 'unknown',
                            'reason': reason
                        })
            
            return {
                'trace': traces,
                'metrics': metrics,
                'relevant_resources': relevant_resources
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trace summaries: {e}")
            return {
                "error": str(e),
                "trace": [],
                "metrics": [],
                "relevant_resources": []
            }

# Create a singleton instance
xray_trace_tool = XRayTraceSummariesTool()

@tool
def get_xray_trace_summaries(service_info: str) -> str:
    """
    Get AWS X-Ray trace summaries for a specific service.
    
    Args:
        service_info: JSON string containing service_name, service_type, minutes (optional), and region (optional)
                     Example: {"service_name": "Sample API/Prod", "service_type": "AWS::ApiGateway::Stage", "minutes": 30, "region": "ap-southeast-1"}
        
    Returns:
        JSON string containing the trace summaries
    """
    try:
        # Parse the service info
        service_data = json.loads(service_info)
        
        service_name = service_data.get('service_name', '')
        service_type = service_data.get('service_type', '')
        minutes = int(service_data.get('minutes', 30))  # Default to 30 minutes
        region = service_data.get('region')
        max_traces = int(service_data.get('max_traces', 5))  # Default to 5 traces
        filter_errors = service_data.get('filter_errors', True)
        
        if not service_name or not service_type:
            return json.dumps({
                "error": "Missing required parameters: service_name and service_type",
                "trace_summaries": []
            })
        
        # Use the provided region or default
        if region and region != xray_trace_tool.region_name:
            tool_instance = XRayTraceSummariesTool(region_name=region)
            logger.info(f"Created new XRayTraceSummariesTool instance with region: {region}")
        else:
            tool_instance = xray_trace_tool
            logger.info(f"Using existing XRayTraceSummariesTool instance with region: {xray_trace_tool.region_name}")
        
        # Get the trace summaries
        trace_data = tool_instance.get_trace_summaries(
            service_name=service_name,
            service_type=service_type,
            minutes=minutes,
            max_traces=max_traces,
            filter_errors=filter_errors
        )
        
        # Log the results
        trace_count = len(trace_data.get('trace_summaries', []))
        logger.info(f"Retrieved {trace_count} trace summaries for {service_name} ({service_type})")
        
        # If no traces found and minutes is less than 360, try with a longer time range
        if trace_count == 0 and minutes < 360:
            extended_minutes = min(360, minutes * 2)  # Double the time range, but cap at 6 hours
            logger.info(f"No traces found in {minutes} minutes, trying with {extended_minutes} minutes")
            
            trace_data = tool_instance.get_trace_summaries(
                service_name=service_name,
                service_type=service_type,
                minutes=extended_minutes,
                max_traces=max_traces,
                filter_errors=filter_errors
            )
            
            trace_count = len(trace_data.get('trace_summaries', []))
            logger.info(f"Retrieved {trace_count} trace summaries with extended time range")
            
            # Update the time range in the response
            trace_data['minutes'] = extended_minutes
        
        # Return as JSON string
        return json.dumps(trace_data, default=str)
        
    except Exception as e:
        return json.dumps({
            "error": f"Error getting X-Ray trace summaries: {str(e)}",
            "trace_summaries": []
        })

# @tool
def analyze_xray_traces(trace_data_str: str) -> str:
    """
    Analyze AWS X-Ray trace summaries to extract key findings.
    
    Args:
        trace_data_str: JSON string containing trace data from get_xray_trace_summaries
        
    Returns:
        JSON string containing analysis results
    """
    try:
        # Parse the trace data
        trace_data = json.loads(trace_data_str)
        
        # Use the singleton instance
        tool_instance = xray_trace_tool
        
        # Analyze the trace summaries
        analysis = tool_instance.analyze_trace_summaries(trace_data)
        
        # Return as JSON string
        return json.dumps(analysis, default=str)
        
    except Exception as e:
        logger.error(f"Error analyzing X-Ray traces: {e}", exc_info=True)
        return json.dumps({
            "error": f"Error analyzing X-Ray traces: {str(e)}",
            "trace": [],
            "metrics": [],
            "relevant_resources": []
        })
