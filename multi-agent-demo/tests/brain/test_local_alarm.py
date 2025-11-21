"""Local test for alarm processing and notification."""

import os
import sys
import boto3
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from aiops.orchestrator.brain_agent import BrainAgent
from aiops.utils.dynamodb_helper import InvestigationStore

# Sample CloudWatch alarm
ALARM_TEXT = """
AlarmName: HighCPUUtilization-i-1234567890abcdef0
AlarmDescription: CPU utilization has exceeded 90% for 5 minutes
MetricName: CPUUtilization
Namespace: AWS/EC2
Dimensions: {"InstanceId": "i-1234567890abcdef0"}
Threshold: 90
ComparisonOperator: GreaterThanThreshold
StateValue: ALARM
StateReason: Threshold Crossed: 1 datapoint [95.2] was greater than the threshold (90.0)
Timestamp: 2025-11-04T11:30:00Z
"""

def test_brain_agent():
    """Test Brain Agent alarm processing."""
    print("=" * 60)
    print("Testing Brain Agent")
    print("=" * 60)
    
    brain = BrainAgent()
    investigation_id = brain.process_alarm_text(ALARM_TEXT)
    
    print(f"\n✅ Investigation created: {investigation_id}")
    
    # Retrieve workflow from DynamoDB
    store = InvestigationStore()
    workflow = store.get_workflow(investigation_id)
    
    print("\n📋 Stored Workflow:")
    print(f"Status: {workflow.get('status')}")
    print(f"Alarm Summary: {workflow.get('alarm_summary', {})}")
    print(f"\nTasks ({len(workflow.get('tasks', []))}):")
    for task in workflow.get('tasks', []):
        print(f"  - {task['task_id']}: {task['agent_type']}")
        print(f"    Description: {task['description']}")
        print(f"    Priority: {task['priority']}")
        print(f"    Status: {task['status']}")
    
    return workflow

def verify_sqs_message(investigation_id: str):
    """Verify SQS message was sent."""
    print("\n" + "=" * 60)
    print("Verifying SQS Message")
    print("=" * 60)
    
    queue_url = os.getenv('INVESTIGATION_QUEUE_URL')
    if not queue_url:
        print("⚠️  INVESTIGATION_QUEUE_URL not set, skipping verification")
        return
    
    sqs = boto3.client('sqs')
    
    # Check queue for message
    response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=2
    )
    
    messages = response.get('Messages', [])
    if messages:
        message_body = json.loads(messages[0]['Body'])
        print(f"\n📨 Message content:")
        print(json.dumps(message_body, indent=2))
        
        if message_body.get('investigation_id') == investigation_id:
            print(f"\n✅ SQS message verified for investigation {investigation_id}")
            
            # Clean up - delete message
            sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=messages[0]['ReceiptHandle']
            )
            print(f"✅ Message deleted from queue")
        else:
            print(f"\n⚠️  SQS message found but investigation_id mismatch")
            print(f"   Expected: {investigation_id}")
            print(f"   Found: {message_body.get('investigation_id')}")
    else:
        print(f"⚠️  No SQS message found (may have been consumed already)")

if __name__ == "__main__":
    # Check environment
    gateway_url = os.getenv("NOTIFICATION_GATEWAY_URL")
    if not gateway_url:
        print("❌ Error: NOTIFICATION_GATEWAY_URL not set")
        sys.exit(1)
    
    print(f"✅ Gateway URL: {gateway_url}\n")
    
    investigation_id = None
    try:
        # Run tests
        workflow = test_brain_agent()
        investigation_id = workflow.get('investigation_id')
        
        # Verify SQS message
        verify_sqs_message(investigation_id)
        
        print("\n" + "=" * 60)
        print("✅ Test completed!")
        print("=" * 60)
    finally:
        # Cleanup
        if investigation_id:
            print(f"\n🧹 Cleaning up investigation {investigation_id}...")
            store = InvestigationStore()
            store.delete_investigation(investigation_id)
            print("✅ Cleanup completed!")
