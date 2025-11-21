#!/usr/bin/env python3
"""Check SQS queue status."""

import boto3
import os

queue_url = os.getenv('INVESTIGATION_QUEUE_URL')

if not queue_url:
    print("❌ INVESTIGATION_QUEUE_URL not set")
    print("Run: ./scripts/export_gateway_urls.sh")
    exit(1)

sqs = boto3.client('sqs')

try:
    response = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=[
            'ApproximateNumberOfMessages',
            'ApproximateNumberOfMessagesNotVisible',
            'ApproximateNumberOfMessagesDelayed'
        ]
    )
    
    attrs = response['Attributes']
    available = int(attrs.get('ApproximateNumberOfMessages', 0))
    in_flight = int(attrs.get('ApproximateNumberOfMessagesNotVisible', 0))
    delayed = int(attrs.get('ApproximateNumberOfMessagesDelayed', 0))
    
    print(f"📊 SQS Queue Status")
    print(f"   Queue: {queue_url}")
    print(f"   Available: {available}")
    print(f"   In Flight: {in_flight}")
    print(f"   Delayed: {delayed}")
    print(f"   Total: {available + in_flight + delayed}")
    
except Exception as e:
    print(f"❌ Error: {e}")
