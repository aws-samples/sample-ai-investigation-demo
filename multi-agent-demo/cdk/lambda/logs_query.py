import json
import boto3
import time

logs = boto3.client('logs')

def lambda_handler(event, context):
    """Query CloudWatch Logs."""
    print("Received event:", event)
    log_group = event.get('log_group_name')
    query_string = event.get('query_string', 'fields @timestamp, @message | limit 20')
    
    # Default to last 30 minutes if times not provided
    current_time = int(time.time())
    one_day_ago = current_time - 86400
    
    # Validate end_time: if older than 1 day or in future, use current time
    end_time = int(event.get('end_time', current_time))
    if end_time < one_day_ago or end_time > current_time:
        print(f"Adjusting end_time from {end_time} to {current_time}")
        end_time = current_time
    
    # Validate start_time: if older than 1 day, use 30 minutes before end_time
    start_time = int(event.get('start_time', end_time - 1800))
    if start_time < one_day_ago:
        print(f"Adjusting start_time from {start_time} to {end_time - 1800}")
        start_time = end_time - 1800
    
    # Ensure start_time < end_time
    if start_time >= end_time:
        print(f"start_time >= end_time, adjusting to 30 min window")
        start_time = end_time - 1800
    
    if not log_group:
        return {
            'content': [{
                'type': 'text',
                'text': json.dumps({'error': 'log_group_name is required'})
            }]
        }
    
    # Start query
    try:
        response = logs.start_query(
            logGroupName=log_group,
            startTime=start_time,
            endTime=end_time,
            queryString=query_string
        )
    except Exception as e:
        return {
            'content': [{
                'type': 'text',
                'text': json.dumps({'error': f'Failed to start query: {str(e)}'})
            }]
        }
    
    query_id = response['queryId']
    
    # Wait for query to complete
    max_wait = 60
    waited = 0
    while waited < max_wait:
        result = logs.get_query_results(queryId=query_id)
        status = result['status']
        
        if status == 'Complete':
            return {
                'content': [{
                    'type': 'text',
                    'text': json.dumps({
                        'status': 'success',
                        'log_group': log_group,
                        'results': result['results'][:50]
                    }, indent=2)
                }]
            }
        elif status == 'Failed':
            return {
                'content': [{
                    'type': 'text',
                    'text': json.dumps({'error': 'Query failed'})
                }]
            }
        
        time.sleep(1)
        waited += 1
    
    return {
        'content': [{
            'type': 'text',
            'text': json.dumps({'error': 'Query timeout'})
        }]
    }
