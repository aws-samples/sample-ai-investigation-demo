"""Gateway configuration for agent-to-gateway mapping.

Environment Variables (exported from CDK):
    OBSERVABILITY_GATEWAY_URL: URL for observability gateway
    RESOURCES_GATEWAY_URL: URL for AWS resources gateway
    NOTIFICATION_GATEWAY_URL: URL for notification gateway
    AWS_OPS_GATEWAY_URL: URL for AWS operations gateway
"""

import os
from typing import Dict, List

# Agent-to-Gateway mapping with descriptions
AGENT_GATEWAY_CONFIG: Dict[str, Dict[str, any]] = {
    "NotificationAgent": {
        "gateways": ["notification-gateway"],
        "description": "Sends notifications to on-call team via Feishu"
    },
    "LogsAgent": {
        "gateways": ["observability-gateway"],
        "description": "Queries CloudWatch Logs for errors, warnings, and patterns"
    },
    "TraceGraphAgent": {
        "gateways": ["observability-gateway"],
        "description": "Analyzes X-Ray service graph for distributed system topology and dependencies. It can also helps to find real service name/ID from alarms"
    },
    "ChangeDetectionAgent": {
        "gateways": ["aws-ops-gateway"],
        "description": "Queries CloudTrail for resource changes and uses AWS CLI to get resource details"
    },

    # "MetricsAgent": {
    #     "gateways": ["observability-gateway"],
    #     "description": "Queries CloudWatch Metrics for performance data and trends"
    # },
}

# Gateway URLs from environment
GATEWAY_URLS: Dict[str, str] = {
    "notification-gateway": os.getenv("NOTIFICATION_GATEWAY_URL", ""),
    "observability-gateway": os.getenv("OBSERVABILITY_GATEWAY_URL", ""),
    "aws-ops-gateway": os.getenv("AWS_OPS_GATEWAY_URL", ""),
}

def get_gateways_for_agent(agent_name: str) -> List[str]:
    """Get list of gateway names for an agent."""
    config = AGENT_GATEWAY_CONFIG.get(agent_name, {})
    return config.get("gateways", [])

def get_agent_description(agent_name: str) -> str:
    """Get description of what an agent can do."""
    config = AGENT_GATEWAY_CONFIG.get(agent_name, {})
    return config.get("description", "")

def get_gateway_url(gateway_name: str) -> str:
    """Get URL for a gateway."""
    return GATEWAY_URLS.get(gateway_name, "")
