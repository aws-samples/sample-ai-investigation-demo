import json
import boto3
from datetime import datetime, timedelta

xray = boto3.client('xray')

def handler(event, context):
    """Query X-Ray service graph for analysis."""
    print(event)
    try:
        body = event # json.loads(event.get('body', '{}'))
        
        # Parse parameters
        start_time = body.get('start_time')
        end_time = body.get('end_time')
        
        # Default to last 15 minutes if not provided
        if not start_time:
            start_time = datetime.utcnow() - timedelta(minutes=15)
        else:
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        
        if not end_time:
            end_time = datetime.utcnow()
        else:
            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # Get service graph
        response = xray.get_service_graph(
            StartTime=start_time,
            EndTime=end_time
        )
        
        print(response)
        services = response.get('Services', [])
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'service_count': len(services),
                'services': services,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }, default=str)
        }
        
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
