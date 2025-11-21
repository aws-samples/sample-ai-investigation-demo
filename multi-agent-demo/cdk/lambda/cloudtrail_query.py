import json
import boto3
from datetime import datetime, timedelta

cloudtrail = boto3.client('cloudtrail')

def lambda_handler(event, context):
    """Query CloudTrail events to find who made changes to AWS resources."""
    try:
        # MCP gateway passes parameters directly in event, not in body
        body = event if isinstance(event, dict) else json.loads(event.get('body', '{}'))
        print(f"[DEBUG] Input body: {json.dumps(body)}")
        
        # Extract parameters
        resource_name = body.get('resource_name')
        resource_type = body.get('resource_type')
        start_time = body.get('start_time')
        end_time = body.get('end_time')
        event_name = body.get('event_name')
        
        print(f"[DEBUG] Parsed params - resource_name: {resource_name}, resource_type: {resource_type}, event_name: {event_name}")
        
        # Default time range: last 24 hours
        if not end_time:
            end_time = datetime.utcnow()
        else:
            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
        if not start_time:
            start_time = end_time - timedelta(hours=24)
        else:
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        
        print(f"[DEBUG] Time range: {start_time} to {end_time}")
        
        # CloudTrail LookupAttributes only supports ONE attribute at a time
        # Priority: ResourceName > EventName > ResourceType
        lookup_attr = None
        if resource_name:
            lookup_attr = {
                'AttributeKey': 'ResourceName',
                'AttributeValue': resource_name
            }
        elif event_name:
            lookup_attr = {
                'AttributeKey': 'EventName',
                'AttributeValue': event_name
            }
        elif resource_type:
            lookup_attr = {
                'AttributeKey': 'ResourceType',
                'AttributeValue': resource_type
            }
        
        print(f"[DEBUG] Lookup attribute: {lookup_attr}")
        
        # Query CloudTrail
        params = {
            'StartTime': start_time,
            'EndTime': end_time,
            'MaxResults': 50
        }
        if lookup_attr:
            params['LookupAttributes'] = [lookup_attr]
        
        print(f"[DEBUG] CloudTrail params: {json.dumps(params, default=str)}")
        response = cloudtrail.lookup_events(**params)
        print(f"[DEBUG] CloudTrail returned {len(response.get('Events', []))} events")
        
        # Format and filter events
        events = []
        for event in response.get('Events', []):
            ct_event = json.loads(event.get('CloudTrailEvent', '{}'))
            
            # Apply additional filters if needed
            if resource_name and lookup_attr and lookup_attr['AttributeKey'] != 'ResourceName':
                # For S3, check bucket name in multiple places
                resources = event.get('Resources', [])
                resource_names = [r.get('ResourceName', '') for r in resources]
                
                # Check request parameters for bucket name
                req_params = ct_event.get('requestParameters', {})
                bucket_name = req_params.get('bucketName', '')
                
                print(f"[DEBUG] Filtering event {event['EventName']} - resources: {resource_names}, bucket: {bucket_name}")
                
                # Check if resource_name matches
                if (resource_name not in resource_names and 
                    resource_name != bucket_name and
                    not any(resource_name in rn for rn in resource_names)):
                    print(f"[DEBUG] Event filtered out - no match")
                    continue
            
            events.append({
                'event_time': event['EventTime'].isoformat(),
                'event_name': event['EventName'],
                'username': event.get('Username', 'N/A'),
                'resources': event.get('Resources', []),
                'cloud_trail_event': ct_event
            })
        
        print(f"[DEBUG] Returning {len(events)} events after filtering")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'events': events,
                'count': len(events)
            })
        }
        
    except Exception as e:
        print(f"[ERROR] Exception: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
