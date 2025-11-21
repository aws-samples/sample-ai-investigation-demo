"""
CloudTrail Changes Tool - LangChain wrapper for retrieving resource modification changes from CloudTrail
"""

import json
import boto3
from datetime import datetime, timedelta
from langchain_core.tools import tool

class CloudTrailChangesTool:
    """Tool for retrieving resource modification changes from CloudTrail."""
    
    def __init__(self):
        self.cloudtrail_client = boto3.client('cloudtrail')
    
    def get_resource_changes(self, minutes: int = 60, event_names: list = None, 
                            resource_types: list = None, resource_names: list = None, 
                            users: list = None, region: str = None):
        """
        Get resource modification changes from CloudTrail for the specified time period.
        
        Args:
            minutes: Number of minutes to look back (default: 60)
            event_names: List of CloudTrail event names to filter (optional)
            resource_types: List of resource types to filter (optional)
            resource_names: List of resource names to filter (optional)
            users: List of IAM users to filter (optional)
            region: AWS region to filter events (optional)
            
        Returns:
            Dictionary containing CloudTrail events and analysis
        """
        try:
            # Calculate start and end time
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=minutes)
            
            # Build lookup attributes for filtering
            lookup_attributes = []
            
            if event_names:
                lookup_attributes.append({
                    'AttributeKey': 'EventName',
                    'AttributeValue': event_names[0]  # Can only filter by one at a time in API
                })
            
            if resource_types:
                lookup_attributes.append({
                    'AttributeKey': 'ResourceType',
                    'AttributeValue': resource_types[0]
                })
                
            if resource_names:
                lookup_attributes.append({
                    'AttributeKey': 'ResourceName',
                    'AttributeValue': resource_names[0]
                })
                
            if users:
                lookup_attributes.append({
                    'AttributeKey': 'Username',
                    'AttributeValue': users[0]
                })
                
            # Build API request parameters
            params = {
                'StartTime': start_time,
                'EndTime': end_time,
                'MaxResults': 50  # Limit results to avoid large responses
            }
            
            # Add lookup attributes if specified
            if lookup_attributes:
                # CloudTrail API can only accept one lookup attribute at a time
                params['LookupAttributes'] = [lookup_attributes[0]]
            
            # Execute the CloudTrail lookup
            response = self.cloudtrail_client.lookup_events(**params)
            
            # Process and filter the events
            events = response.get('Events', [])
            filtered_events = []
            
            for event in events:
                event_data = {
                    'EventId': event.get('EventId'),
                    'EventName': event.get('EventName'),
                    'EventTime': event.get('EventTime').isoformat() if isinstance(event.get('EventTime'), datetime) else event.get('EventTime'),
                    'Username': event.get('Username'),
                    'Resources': event.get('Resources', []),
                    'CloudTrailEvent': json.loads(event.get('CloudTrailEvent', '{}')),
                }
                
                # Apply additional filtering if needed
                should_include = True
                
                if event_names and len(event_names) > 1 and event_data['EventName'] not in event_names:
                    should_include = False
                    
                if region and event_data['CloudTrailEvent'].get('awsRegion') != region:
                    should_include = False
                
                # Add more filtering logic as needed
                
                if should_include:
                    filtered_events.append(event_data)
            
            # Create summary of changes
            summary = {
                'total_events': len(filtered_events),
                'event_types': {},
                'affected_resources': {},
                'users': {}
            }
            
            for event in filtered_events:
                # Count event types
                event_name = event['EventName']
                summary['event_types'][event_name] = summary['event_types'].get(event_name, 0) + 1
                
                # Count affected resources
                for resource in event.get('Resources', []):
                    resource_type = resource.get('ResourceType', 'Unknown')
                    summary['affected_resources'][resource_type] = summary['affected_resources'].get(resource_type, 0) + 1
                
                # Count users
                username = event.get('Username', 'Unknown')
                summary['users'][username] = summary['users'].get(username, 0) + 1
            
            return {
                'events': filtered_events,
                'summary': summary,
                'query_parameters': {
                    'minutes': minutes,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'event_names': event_names,
                    'resource_types': resource_types,
                    'resource_names': resource_names,
                    'users': users,
                    'region': region
                }
            }
            
        except Exception as e:
            return {
                'error': f"Failed to retrieve CloudTrail events: {str(e)}",
                'query_parameters': {
                    'minutes': minutes,
                    'event_names': event_names,
                    'resource_types': resource_types,
                    'resource_names': resource_names,
                    'users': users,
                    'region': region
                }
            }


@tool("get_resource_changes")
def get_resource_changes(input_params: str) -> str:
    """Get resource modification changes from CloudTrail for the last X minutes.
    
    Args:
        input_params: JSON string with parameters:
            - minutes: Number of minutes to look back (default: 60)
            - event_names: Comma-separated list of CloudTrail event names to filter (optional)
            - resource_types: Comma-separated list of resource types to filter (optional)
            - resource_names: Comma-separated list of resource names to filter (optional)
            - users: Comma-separated list of IAM users to filter (optional)
            - region: AWS region to filter events (optional)
    
    Returns:
        JSON string containing CloudTrail events and analysis
    """
    try:
        # Parse input parameters
        if isinstance(input_params, str):
            try:
                params = json.loads(input_params)
            except json.JSONDecodeError:
                # If not JSON, treat as simple parameters
                params = {"minutes": 60, "resource_names": input_params}
        else:
            params = input_params if isinstance(input_params, dict) else {"minutes": 60}
        
        # Extract parameters with defaults
        minutes = params.get("minutes", 60)
        event_names = params.get("event_names")
        resource_types = params.get("resource_types")
        resource_names = params.get("resource_names")
        users = params.get("users")
        region = params.get("region")
        
        # Ensure minutes is an integer
        if isinstance(minutes, str):
            minutes = int(minutes)
        
        # Parse comma-separated strings into lists
        event_names_list = event_names.split(',') if event_names else None
        resource_types_list = resource_types.split(',') if resource_types else None
        resource_names_list = resource_names.split(',') if resource_names else None
        users_list = users.split(',') if users else None
        
        # Create tool and execute
        cloudtrail_tool = CloudTrailChangesTool()
        result = cloudtrail_tool.get_resource_changes(
            minutes=minutes,
            event_names=event_names_list,
            resource_types=resource_types_list,
            resource_names=resource_names_list,
            users=users_list,
            region=region
        )
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({
            "error": f"Failed to retrieve resource changes: {str(e)}",
            "input_received": str(input_params),
            "error_type": type(e).__name__
        }, indent=2)
