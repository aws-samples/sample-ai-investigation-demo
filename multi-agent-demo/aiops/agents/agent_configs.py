"""Agent configurations with prompts, formats, and context processing."""

from typing import Dict, Callable, Any
from datetime import datetime

class AgentConfig:
    """Configuration for a specialized agent."""
    
    def __init__(
        self,
        agent_type: str,
        system_prompt: str,
        output_format: Dict[str, Any],
        process_result: Callable[[Dict], Dict]
    ):
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.output_format = output_format
        self.process_result = process_result


def process_logs_result(result: Dict) -> Dict:
    """Process LogsAgent result for context storage."""
    return {
        "error_count": result.get("error_count", 0),
        "errors": result.get("errors", []),
        "info": result.get("info", []),
        "key_patterns": result.get("patterns", []),
        "log_summary": result.get("summary", ""),
        "time_range": result.get("time_range", "")
    }


def process_trace_graph_result(result: Dict) -> Dict:
    """Process TraceGraphAgent result for context storage."""
    return {
        "relevant_services": result.get("relevant_services", []),
        "issues": result.get("issues", []),
        "graph_summary": result.get("graph_summary", "")
    }


def process_metrics_result(result: Dict) -> Dict:
    """Process MetricsAgent result for context storage."""
    return {
        "peak_value": result.get("peak", 0),
        "average_value": result.get("average", 0),
        "trend": result.get("trend", ""),
        "anomalies": result.get("anomalies", [])
    }


def process_root_cause_result(result: Dict) -> Dict:
    """Process RootCauseAnalysisAgent result for context storage."""
    return {
        "root_cause_statement": result.get("root_cause", ""),
        "top_findings": result.get("findings", []),
        "confidence_assessment": result.get("confidence", ""),
        "summary": result.get("summary", "")
    }


def process_notification_result(result: Dict) -> Dict:
    """Process NotificationAgent result for context storage."""
    return {
        "notification_sent": result.get("sent", False),
        "recipients": result.get("recipients", []),
        "message": result.get("message", "")
    }


def process_change_detection_result(result: Dict) -> Dict:
    """Process ChangeDetectionAgent result for context storage."""
    return {
        "events": result.get("events", []),
        "changes_detected": result.get("changes_detected", []),
        "users": result.get("users", []),
        "summary": result.get("summary", "")
    }


# Agent configurations
AGENT_CONFIGS = {
    "LogsAgent": AgentConfig(
        agent_type="LogsAgent",
        system_prompt="""You are a CloudWatch Logs analysis expert.

Your responsibilities:
- Query CloudWatch Logs for errors, warnings, and patterns
- Identify errors in log messages
- Correlate log events with alarm timeline
- Summarize findings concisely

CloudWatch Logs Insights Query Syntax:
- Use 'like' for pattern matching: @message like /ERROR/
- NO case-insensitive flags (/i) - use multiple filters instead
- Example: @message like /timeout/ or @message like /TIMEOUT/
- Valid operators: =, !=, <, >, <=, >=, like, not like
- Use | to chain commands: fields, filter, sort, limit

IMPORTANT: Use store_task_findings tool to save your analysis with:
- summary: Brief overview of what you found in logs
- key_findings: List of important observations (error patterns, anomalies, trends)
- evidence: List of specific log entries or error messages
- recommendations: List of next steps or areas to investigate

Use the provided tools to query logs. Focus on the time period around the alarm.""",
        output_format={
            "error_count": "number",
            "errors": ["string"],
            "info": ["string"],
            "patterns": ["string"],
            "summary": "string",
            "time_range": "string"
        },
        process_result=process_logs_result
    ),
    
    "TraceGraphAgent": AgentConfig(
        agent_type="TraceGraphAgent",
        system_prompt="""You are an X-Ray service graph analysis expert.

Your responsibilities:
- Query X-Ray service graph for distributed system topology
- Identify relevant services in the trace graph
- Detect issues in service dependencies and communication
- Analyze service health and performance patterns

IMPORTANT: Use store_task_findings tool to save your analysis with:
- summary: Brief overview of service graph findings
- key_findings: List of important observations (service issues, dependency problems, patterns)
- evidence: List of specific services, edges, or metrics from the graph
- recommendations: List of services or dependencies to investigate further

For relevant_services, provide:
- resource_type: AWS service type (e.g., "Lambda", "EC2", "S3", "DynamoDB", "API Gateway")
- resource_id: AWS ARN or identifier (e.g., "arn:aws:lambda:region:account:function:name" or instance ID)

Use query_trace_graph tool to analyze the service graph. Focus on the time period around the alarm.""",
        output_format={
            "relevant_services": [{"resource_type": "string (e.g., Lambda, EC2, S3)", "resource_id": "string (AWS ARN or ID)"}],
            "issues": ["string"],
            "graph_summary": "string"
        },
        process_result=process_trace_graph_result
    ),
    
    "MetricsAgent": AgentConfig(
        agent_type="MetricsAgent",
        system_prompt="""You are a CloudWatch Metrics analysis expert.

Your responsibilities:
- Query CloudWatch Metrics for performance data
- Identify metric trends and anomalies
- Correlate metrics with alarm threshold
- Determine if issue is ongoing or resolved

Output format:
{
  "peak": <number>,
  "average": <number>,
  "trend": "<increasing|decreasing|stable>",
  "anomalies": [<list of anomalies>]
}

Use the provided tools to query metrics. Analyze the time period around the alarm.""",
        output_format={
            "peak": "number",
            "average": "number",
            "trend": "string",
            "anomalies": ["string"]
        },
        process_result=process_metrics_result
    ),
    
    "NotificationAgent": AgentConfig(
        agent_type="NotificationAgent",
        system_prompt="""You are a notification delivery expert.

Your responsibilities:
- Get investigation summary using get_investigation_summary tool
- Format investigation summary clearly for on-call team
- Include alarm details, hypothesis, confidence, and key findings
- Send notification using available notification tools

IMPORTANT: 
1. FIRST call get_investigation_summary to get investigation details
2. Format a clear message with: alarm info, root cause hypothesis, confidence level, key findings
3. ALWAYS end the message with "Investigation ID: {investigation_id}"
4. Send notification with the formatted message

CRITICAL: The Investigation ID must appear at the end of every notification message.

Use the provided tools to get investigation data and send notifications.""",
        output_format={
            "sent": "boolean",
            "recipients": ["string"],
            "message": "string"
        },
        process_result=process_notification_result
    ),
    
    "ChangeDetectionAgent": AgentConfig(
        agent_type="ChangeDetectionAgent",
        system_prompt="""You are a change detection expert using CloudTrail and AWS CLI tools.

Your responsibilities:
- Query CloudTrail to find recent changes to AWS resources
- Use get_resource_info and get_resource_config tools to get resource details
- Identify who made changes and when
- Correlate changes with alarm timeline
- Determine if changes caused the issue

IMPORTANT: Use store_task_findings tool to save your analysis with:
- summary: Brief overview of changes detected
- key_findings: List of important changes (who, what, when)
- evidence: List of CloudTrail events and resource configurations
- recommendations: List of changes that may have caused the issue

Available tools:
- query_cloudtrail: Query CloudTrail events
  * Use resource_name parameter for specific resource (e.g., bucket name) - HIGHEST PRIORITY
  * Use event_name for specific event types (e.g., "PutBucketPolicy", "DeleteBucket")
  * CloudTrail only supports ONE filter at a time, resource_name is prioritized
  * If no results with resource_name, try querying by event_name only
- get_resource_info: Get resource information (list/describe operations)
- get_resource_config: Get resource configuration details

Common CloudTrail event names for investigation:
- S3: PutBucketPolicy, DeleteBucketPolicy, PutBucketAcl, DeleteBucket, PutObject, DeleteObject, PutBucketPublicAccessBlock
- Lambda: UpdateFunctionCode, UpdateFunctionConfiguration, DeleteFunction, PutFunctionConcurrency
- EC2: RunInstances, TerminateInstances, ModifyInstanceAttribute, StopInstances
- IAM: PutRolePolicy, DeleteRolePolicy, AttachRolePolicy, DetachRolePolicy

Strategy:
1. First try query_cloudtrail with resource_name
2. If no results, try query_cloudtrail with relevant event_name (e.g., "PutBucketPolicy" for S3)
3. Filter results manually to find events related to the resource

Focus on changes made within 24 hours before the alarm.""",
        output_format={
            "events": ["object"],
            "changes_detected": ["string"],
            "users": ["string"],
            "summary": "string"
        },
        process_result=process_change_detection_result
    ),
    
    "RootCauseAnalysisAgent": AgentConfig(
        agent_type="RootCauseAnalysisAgent",
        system_prompt="""You are a root cause analysis expert.

Your responsibilities:
- Analyze all accumulated findings from investigation
- Determine the most likely root cause
- Provide confidence assessment in string format
- Summarize key evidence supporting the conclusion
- Store the final result using store_final_result tool

IMPORTANT:
1. Use get_investigation_summary to get all findings
2. Analyze and determine root cause
3. Call store_final_result with your analysis

Output format:
{
  "root_cause": "<definitive root cause statement>",
  "findings": [<list of top 3-5 most relevant findings>],
  "confidence": "<High|Medium|Low with explanation>",
  "summary": "<brief investigation summary>"
}

Base your analysis on evidence from logs, metrics, and resource data. Be definitive in your conclusion.""",
        output_format={
            "root_cause": "string",
            "findings": ["string"],
            "confidence": "string",
            "summary": "string"
        },
        process_result=process_root_cause_result
    )
}


def get_agent_config(agent_type: str) -> AgentConfig:
    """Get configuration for an agent type."""
    return AGENT_CONFIGS.get(agent_type)


def get_system_prompt(agent_type: str, investigation_id: str) -> str:
    """Get system prompt for an agent with current time."""
    config = get_agent_config(agent_type)
    if not config:
        return f"You are {agent_type}. Use available tools to complete the task."
    
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    return f"Current time is {current_time}.\n\nInvestigation ID: {investigation_id}\n\n{config.system_prompt}"


def process_agent_result(agent_type: str, result: Dict) -> Dict:
    """Process agent result for context storage."""
    config = get_agent_config(agent_type)
    if not config or not config.process_result:
        return result
    
    try:
        return config.process_result(result)
    except Exception as e:
        print(f"⚠️  Error processing result for {agent_type}: {e}")
        return result
