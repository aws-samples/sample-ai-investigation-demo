"""
Alarm Knowledge Base for AIOps workflow
This module provides RAG-style access to information about AWS alarms,
their purposes, and troubleshooting steps.
"""

import json
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool

# Alarm knowledge base
ALARM_KNOWLEDGE = {
    "GetProductByIdErrorHigh": {
        "description": "This is the product service API get product by ID alarm. If API experience severe infrastructure or coding issue, this alarm will be triggered. With this alarm triggered, it means over 5% of the API call is not functional.",
        "purpose": "Detect service availability issues or coding errors in the product service API",
        "severity": "High",
        "x_ray_investigation": "Check X-Ray traces with attribute service(id(name: \"demo-app\" , type: \"AWS::EC2::Instance\" ))"
    },
    "CPUUtilizationHigh": {
        "description": "Triggers when CPU utilization exceeds 80% for 5 minutes",
        "purpose": "Detect potential performance issues or resource constraints on instances",
        "troubleshooting": [
            "Check the instance load using CloudWatch metrics",
            "Review application logs for unusual activity",
            "Consider scaling up the instance or adding more instances",
            "Look for runaway processes or inefficient code"
        ],
        "related_resources": ["EC2", "Auto Scaling Groups"],
        "severity": "Medium",
        "x_ray_investigation": "Check X-Ray traces for slow API calls or database queries that might be causing high CPU"
    },
    "MemoryUtilizationHigh": {
        "description": "Triggers when memory utilization exceeds 85% for 5 minutes",
        "purpose": "Detect memory leaks or insufficient memory allocation",
        "troubleshooting": [
            "Check application logs for memory-related errors",
            "Review memory usage patterns in CloudWatch",
            "Consider increasing instance memory or optimizing application",
            "Look for memory leaks in application code"
        ],
        "related_resources": ["EC2", "Lambda"],
        "severity": "High",
        "x_ray_investigation": "Use X-Ray to identify functions or services consuming excessive memory"
    },
    "APIGateway5xxErrors": {
        "description": "Triggers when 5xx errors exceed 1% of total requests over 5 minutes",
        "purpose": "Detect backend service failures or configuration issues",
        "troubleshooting": [
            "Check Lambda or EC2 logs for errors",
            "Verify integration endpoint health",
            "Review recent deployments or configuration changes",
            "Check for throttling or quota limits"
        ],
        "related_resources": ["API Gateway", "Lambda", "EC2"],
        "severity": "Critical",
        "x_ray_investigation": "Use X-Ray to trace requests through API Gateway to backend services and identify failing components"
    },
    "DynamoDBThrottledRequests": {
        "description": "Triggers when read/write throttled requests exceed threshold",
        "purpose": "Detect insufficient provisioned capacity or hot partitions",
        "troubleshooting": [
            "Review provisioned capacity vs actual usage",
            "Check for uneven access patterns across partition keys",
            "Consider enabling auto-scaling or increasing capacity",
            "Optimize application access patterns"
        ],
        "related_resources": ["DynamoDB"],
        "severity": "Medium",
        "x_ray_investigation": "Use X-Ray to identify which operations are being throttled and their frequency"
    },
    "LambdaErrors": {
        "description": "Triggers when Lambda function errors exceed 5% of invocations",
        "purpose": "Detect code errors, configuration issues, or dependency failures",
        "troubleshooting": [
            "Check Lambda logs in CloudWatch",
            "Verify IAM permissions for the Lambda role",
            "Check for timeouts or memory constraints",
            "Review dependencies and external service health"
        ],
        "related_resources": ["Lambda", "CloudWatch Logs"],
        "severity": "High",
        "x_ray_investigation": "Use X-Ray to trace Lambda execution and identify where errors occur in the code or with dependencies"
    },
    "RDSHighCPU": {
        "description": "Triggers when RDS CPU utilization exceeds 80% for 15 minutes",
        "purpose": "Detect database performance issues or resource constraints",
        "troubleshooting": [
            "Review slow query logs",
            "Check for missing indexes or inefficient queries",
            "Consider scaling up the instance or read replicas",
            "Look for unusual database activity or connections"
        ],
        "related_resources": ["RDS", "CloudWatch Logs"],
        "severity": "Medium",
        "x_ray_investigation": "Use X-Ray to identify which application components are making inefficient database calls"
    },
    "ELBHighLatency": {
        "description": "Triggers when load balancer latency exceeds 1 second for 5 minutes",
        "purpose": "Detect backend service performance issues or network problems",
        "troubleshooting": [
            "Check target group health and response times",
            "Review backend service logs and metrics",
            "Check for network issues or routing problems",
            "Consider scaling backend services"
        ],
        "related_resources": ["ELB", "EC2", "Auto Scaling Groups"],
        "severity": "High",
        "x_ray_investigation": "Use X-Ray to trace requests through the load balancer to backend services and identify bottlenecks"
    },
    "S3BucketSizeHigh": {
        "description": "Triggers when S3 bucket size exceeds predefined threshold",
        "purpose": "Monitor storage costs and prevent unexpected growth",
        "troubleshooting": [
            "Review bucket contents and usage patterns",
            "Check lifecycle policies",
            "Consider implementing object expiration",
            "Look for unusual upload activity"
        ],
        "related_resources": ["S3"],
        "severity": "Low",
        "x_ray_investigation": "Not typically applicable for S3 storage issues"
    }
}

@tool("get_alarm_info")
def get_alarm_info(alarm_description: str = "") -> str:
    """
    Get detailed information about AWS alarms based on the provided description.
    If no description is provided, returns information about all alarms.
    
    Args:
        alarm_description: Optional description or keywords related to the alarm
        
    Returns:
        String containing detailed information about matching alarms
    """
    # If no description provided, return all alarms
    if not alarm_description.strip():
        return json.dumps(ALARM_KNOWLEDGE, indent=2)
    
    # Return all alarms and let the LLM determine the best match
    return json.dumps(ALARM_KNOWLEDGE, indent=2)

@tool("list_alarms")
def list_alarms() -> str:
    """
    List all available alarms in the knowledge base with their details.
    
    Returns:
        String containing a list of all available alarms with their complete information
    """
    return json.dumps(ALARM_KNOWLEDGE, indent=2)

@tool("get_xray_trace_instructions")
def get_xray_trace_instructions(alarm_description: str = "") -> str:
    """
    Get instructions on how to retrieve X-Ray traces for investigating alarms.
    
    Args:
        alarm_description: Optional description or keywords related to the alarm
        
    Returns:
        String containing instructions for retrieving relevant X-Ray traces
    """
    # Return all X-Ray trace instructions and let the LLM determine the best match
    xray_instructions = {}
    for alarm_name, alarm_data in ALARM_KNOWLEDGE.items():
        xray_instructions[alarm_name] = {
            "description": alarm_data["description"],
            "x_ray_investigation": alarm_data["x_ray_investigation"]
        }
    
    # Add general X-Ray trace retrieval steps
    general_steps = {
        "general_steps": {
            "description": "General steps for X-Ray trace retrieval",
            "steps": [
                "1. Open the AWS X-Ray console",
                "2. Go to the 'Traces' section",
                "3. Filter by time range around the alarm trigger time",
                "4. Filter by service name or error status",
                "5. Select traces with high latency or error responses",
                "6. Analyze the trace map and timeline to identify bottlenecks or errors"
            ],
            "aws_cli_commands": [
                "# Get recent traces with errors:",
                "aws xray get-trace-summaries --start-time $(date -d '1 hour ago' +%s) --end-time $(date +%s) --filter-expression \"error = true\"",
                "# Get detailed trace data:",
                "aws xray batch-get-traces --trace-ids <trace-id-1> <trace-id-2>"
            ]
        }
    }
    
    # Combine specific instructions with general steps
    result = {**xray_instructions, **general_steps}
    
    return json.dumps(result, indent=2)
