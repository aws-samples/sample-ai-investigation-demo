"""SQS helper functions for sending investigation messages."""

import boto3
import json
import os
import hashlib
import time
from aiops.models.enums import MessageType
from aiops.utils.online_logger import log

sqs = boto3.client('sqs')

def send_execution_message(investigation_id: str, current_task: str = None) -> bool:
    """Send EXECUTION message to SQS queue.
    
    Args:
        investigation_id: Investigation ID
        current_task: Current task ID for deduplication
        
    Returns:
        True if message sent successfully, False otherwise
    """
    queue_url = os.getenv('INVESTIGATION_QUEUE_URL')
    if not queue_url:
        log("sqs-helper", "INVESTIGATION_QUEUE_URL not configured", level="ERROR", investigation_id=investigation_id)
        return False
    
    try:
        # Use deterministic deduplication ID so duplicate sends are ignored
        dedup_id = hashlib.sha256(f"{investigation_id}-exec-{current_task or 'none'}".encode()).hexdigest()
        
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({
                'message_type': MessageType.EXECUTION.value,
                'investigation_id': investigation_id
            }),
            MessageGroupId=investigation_id,
            MessageDeduplicationId=dedup_id
        )
        
        log("sqs-helper", f"EXECUTION message sent: task={current_task}", investigation_id=investigation_id)
        return True
    except Exception as e:
        log("sqs-helper", f"Failed to send EXECUTION message: {e}", level="ERROR", investigation_id=investigation_id)
        return False


def send_evaluation_message(investigation_id: str, task_id: str = None) -> bool:
    """Send EVALUATION message to SQS queue.
    
    Args:
        investigation_id: Investigation ID
        task_id: Completed task ID for deduplication
        
    Returns:
        True if message sent successfully, False otherwise
    """
    queue_url = os.getenv('INVESTIGATION_QUEUE_URL')
    if not queue_url:
        log("sqs-helper", "INVESTIGATION_QUEUE_URL not configured", level="ERROR", investigation_id=investigation_id)
        return False
    
    try:
        # Use deterministic deduplication ID so duplicate sends are ignored
        dedup_id = hashlib.sha256(f"{investigation_id}-eval-{task_id or 'none'}".encode()).hexdigest()
        
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({
                'message_type': MessageType.EVALUATION.value,
                'investigation_id': investigation_id
            }),
            MessageGroupId=investigation_id,
            MessageDeduplicationId=dedup_id
        )
        
        log("sqs-helper", f"EVALUATION message sent: task={task_id}", investigation_id=investigation_id)
        return True
    except Exception as e:
        log("sqs-helper", f"Failed to send EVALUATION message: {e}", level="ERROR", investigation_id=investigation_id)
        return False
