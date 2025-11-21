#!/usr/bin/env python3
"""Clean up all DynamoDB tables and SQS queues for AIOps."""

import boto3
import os

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

# Clean up DynamoDB tables
tables = [
    'aiops-investigations',
    'aiops-investigation-context',
    'aiops-logs'
]

for table_name in tables:
    try:
        table = dynamodb.Table(table_name)
        
        # Scan and delete all items
        response = table.scan()
        items = response.get('Items', [])
        
        with table.batch_writer() as batch:
            for item in items:
                # Get primary key
                key = {}
                for key_attr in table.key_schema:
                    attr_name = key_attr['AttributeName']
                    key[attr_name] = item[attr_name]
                batch.delete_item(Key=key)
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items = response.get('Items', [])
            
            with table.batch_writer() as batch:
                for item in items:
                    key = {}
                    for key_attr in table.key_schema:
                        attr_name = key_attr['AttributeName']
                        key[attr_name] = item[attr_name]
                    batch.delete_item(Key=key)
        
        print(f"✅ Cleaned up table: {table_name}")
    except Exception as e:
        print(f"❌ Error cleaning table {table_name}: {e}")

# Clean up SQS queue
queue_url = os.getenv('INVESTIGATION_QUEUE_URL')
if queue_url:
    try:
        sqs.purge_queue(QueueUrl=queue_url)
        print(f"✅ Purged SQS queue: {queue_url}")
    except Exception as e:
        print(f"❌ Error purging SQS queue: {e}")
else:
    print("⚠️  INVESTIGATION_QUEUE_URL not set, skipping SQS cleanup")

print("🎉 Cleanup complete!")
