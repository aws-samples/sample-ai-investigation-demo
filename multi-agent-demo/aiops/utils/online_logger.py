"""Online logging to DynamoDB."""

import os
import boto3
from datetime import datetime
from typing import Optional

# Check if online logging is enabled
ONLINE_LOG_ENABLED = os.getenv('ONLINE_LOG', 'false').lower() == 'true'
LOGS_TABLE = os.getenv('LOGS_TABLE', 'aiops-logs')

if ONLINE_LOG_ENABLED:
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(LOGS_TABLE)
else:
    table = None


def log(component: str, message: str, level: str = "INFO", investigation_id: Optional[str] = None):
    """Log message to DynamoDB if ONLINE_LOG is enabled.
    
    Args:
        component: Component name (e.g., "BrainAgent", "ExecutorAgent")
        message: Log message
        level: Log level (INFO, ERROR, WARNING, DEBUG)
        investigation_id: Optional investigation ID for correlation
    """
    # if not ONLINE_LOG_ENABLED or not table:
    #     return

    try:
        item = {
            'component': component,
            'time': datetime.utcnow().isoformat(),
            'level': level,
            'log': message
        }

        if investigation_id:
            item['investigation_id'] = investigation_id

        table.put_item(Item=item)
    except Exception as e:
        # Don't fail if logging fails
        print(f"Failed to write online log: {e}")
