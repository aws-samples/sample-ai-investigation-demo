import json
import os
import boto3
import time

bedrock_agentcore = boto3.client('bedrock-agentcore')

def lambda_handler(event, context):
    agent_runtime_arn = os.environ['AGENT_RUNTIME_ARN']
    print(event)
    failed_messages = []
    
    for record in event['Records']:
        message_body = record['body']
        message_id = record['messageId']
        
        # Retry logic with exponential backoff
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                response = bedrock_agentcore.invoke_agent_runtime(
                    agentRuntimeArn=agent_runtime_arn,
                    qualifier='DEFAULT',
                    payload=message_body.encode('utf-8')
                )
                
                print(f"✅ Invoked AgentCore Runtime (attempt {attempt + 1}): {message_id}")
                break  # Success, exit retry loop

            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed for {message_id}: {str(e)}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    # All retries failed
                    print(f"🚫 All retries exhausted for {message_id}")
                    failed_messages.append({
                        'itemIdentifier': message_id,
                        'error': str(e)
                    })
    
    # Return partial batch failure for SQS to retry failed messages
    if failed_messages:
        return {
            'batchItemFailures': [{'itemIdentifier': msg['itemIdentifier']} for msg in failed_messages]
        }
    
    return {'statusCode': 200}
