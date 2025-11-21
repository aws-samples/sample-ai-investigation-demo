"""
AWS CloudTrail Collector Tool

This tool provides comprehensive methods to collect CloudTrail events and logs
for AWS resources involved in incidents. It can query CloudTrail for specific
time ranges, resource types, and event patterns to help with root cause analysis.

The tool integrates with AWS CloudTrail APIs to gather:
1. API calls and administrative actions
2. Configuration changes
3. Resource access patterns
4. Error events and failures
5. User and role activity
6. Cross-service interactions
"""

import boto3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from botocore.exceptions import ClientError, NoCredentialsError

class CloudTrailCollector:
    """Main class for collecting AWS CloudTrail events and logs"""
    
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize the CloudTrail collector
        
        Args:
            region_name: AWS region to use for API calls
        """
        self.region_name = region_name
        self.logger = logging.getLogger(__name__)
        
        # Initialize AWS clients
        try:
            self.cloudtrail_client = boto3.client('cloudtrail', region_name=region_name)
            self.cloudwatch_client = boto3.client('cloudwatch', region_name=region_name)
            self.sts_client = boto3.client('sts', region_name=region_name)
            
            # Get current account ID
            self.account_id = self.sts_client.get_caller_identity()['Account']
            
            self.logger.info(f"Initialized CloudTrail collector for region: {region_name}, account: {self.account_id}")
            
        except NoCredentialsError:
            self.logger.error("AWS credentials not found. Please configure AWS credentials.")
            raise
        except Exception as e:
            self.logger.error(f"Error initializing CloudTrail collector: {e}")
            raise
    
    def collect_events_for_resources(self, resource_arns: List[str], 
                                   start_time: datetime = None,
                                   end_time: datetime = None,
                                   max_events: int = 100) -> Dict[str, Any]:
        """
        Collect CloudTrail events for specific resources
        
        Args:
            resource_arns: List of AWS resource ARNs
            start_time: Start time for event collection (default: 1 hour ago)
            end_time: End time for event collection (default: now)
            max_events: Maximum number of events to collect per resource
            
        Returns:
            Dictionary containing events for each resource
        """
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=1)
        if not end_time:
            end_time = datetime.utcnow()
        
        self.logger.info(f"Collecting CloudTrail events for {len(resource_arns)} resources from {start_time} to {end_time}")
        
        results = {
            'cloudtrail_data': [],
            'summary': '',
            'time_range': {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            },
            'total_events': 0,
            'errors': []
        }
        
        for resource_arn in resource_arns:
            try:
                resource_events = self._collect_events_for_single_resource(
                    resource_arn, start_time, end_time, max_events
                )
                results['cloudtrail_data'].append(resource_events)
                results['total_events'] += len(resource_events.get('events', []))
                
            except Exception as e:
                error_msg = f"Error collecting events for {resource_arn}: {str(e)}"
                self.logger.error(error_msg)
                results['errors'].append({
                    'resource_arn': resource_arn,
                    'error': error_msg
                })
        
        # Generate summary
        results['summary'] = self._generate_summary(results)
        
        return results
    
    def _collect_events_for_single_resource(self, resource_arn: str,
                                          start_time: datetime,
                                          end_time: datetime,
                                          max_events: int) -> Dict[str, Any]:
        """
        Collect CloudTrail events for a single resource
        
        Args:
            resource_arn: AWS resource ARN
            start_time: Start time for event collection
            end_time: End time for event collection
            max_events: Maximum number of events to collect
            
        Returns:
            Dictionary containing events for the resource
        """
        resource_info = self._parse_resource_arn(resource_arn)
        
        self.logger.info(f"Collecting events for {resource_info['service']} resource: {resource_info['resource_id']}")
        
        # Build lookup attributes based on resource type
        lookup_attributes = self._build_lookup_attributes(resource_info)
        
        events = []
        next_token = None
        
        while len(events) < max_events:
            try:
                # Prepare lookup events parameters
                params = {
                    'StartTime': start_time,
                    'EndTime': end_time,
                    'MaxResults': min(50, max_events - len(events))  # CloudTrail uses MaxResults, not MaxItems
                }
                
                if lookup_attributes:
                    params['LookupAttributes'] = lookup_attributes
                
                if next_token:
                    params['NextToken'] = next_token
                
                response = self.cloudtrail_client.lookup_events(**params)
                
                # Process events
                for event in response.get('Events', []):
                    if self._is_event_relevant(event, resource_info):
                        processed_event = self._process_event(event)
                        events.append(processed_event)
                
                next_token = response.get('NextToken')
                if not next_token:
                    break
                    
            except Exception as e:
                self.logger.error(f"Error in lookup_events for {resource_arn}: {e}")
                break
        
        # Get additional resource-specific metrics
        metrics = self._get_resource_metrics(resource_info, start_time, end_time)
        
        return {
            'resource_name': resource_info['resource_id'],
            'resource_arn': resource_arn,
            'resource_type': resource_info['service'],
            'events': events[:max_events],  # Ensure we don't exceed max_events
            'metrics': metrics,
            'event_count': len(events),
            'time_range': {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        }
    
    def _parse_resource_arn(self, resource_arn: str) -> Dict[str, str]:
        """Parse AWS resource ARN into components"""
        try:
            # ARN format: arn:aws:service:region:account:resource
            parts = resource_arn.split(':')
            if len(parts) >= 6:
                return {
                    'service': parts[2],
                    'region': parts[3],
                    'account': parts[4],
                    'resource_type': parts[5].split('/')[0] if '/' in parts[5] else parts[5],
                    'resource_id': parts[5].split('/')[-1] if '/' in parts[5] else parts[5],
                    'full_resource': ':'.join(parts[5:]) if len(parts) > 6 else parts[5]
                }
            else:
                return {
                    'service': 'unknown',
                    'region': 'unknown',
                    'account': 'unknown',
                    'resource_type': 'unknown',
                    'resource_id': resource_arn,
                    'full_resource': resource_arn
                }
        except Exception as e:
            self.logger.warning(f"Error parsing ARN {resource_arn}: {e}")
            return {
                'service': 'unknown',
                'region': 'unknown',
                'account': 'unknown',
                'resource_type': 'unknown',
                'resource_id': resource_arn,
                'full_resource': resource_arn
            }
    
    def _build_lookup_attributes(self, resource_info: Dict[str, str]) -> List[Dict[str, str]]:
        """Build CloudTrail lookup attributes based on resource type"""
        lookup_attributes = []
        
        service = resource_info['service']
        resource_id = resource_info['resource_id']
        
        # Add resource-specific lookup attributes
        if service == 'ec2':
            if resource_info['resource_type'] == 'instance':
                lookup_attributes.append({
                    'AttributeKey': 'ResourceName',
                    'AttributeValue': resource_id
                })
        elif service == 'lambda':
            lookup_attributes.append({
                'AttributeKey': 'ResourceName',
                'AttributeValue': resource_id
            })
        elif service == 's3':
            lookup_attributes.append({
                'AttributeKey': 'ResourceName',
                'AttributeValue': resource_id
            })
        elif service == 'rds':
            lookup_attributes.append({
                'AttributeKey': 'ResourceName',
                'AttributeValue': resource_id
            })
        elif service == 'dynamodb':
            lookup_attributes.append({
                'AttributeKey': 'ResourceName',
                'AttributeValue': resource_id
            })
        
        return lookup_attributes
    
    def _is_event_relevant(self, event: Dict[str, Any], resource_info: Dict[str, str]) -> bool:
        """Check if a CloudTrail event is relevant to the resource"""
        try:
            # Check if event involves the specific resource
            event_name = event.get('EventName', '')
            resources = event.get('Resources', [])
            
            # Check resources in the event
            for resource in resources:
                resource_name = resource.get('ResourceName', '')
                resource_type = resource.get('ResourceType', '')
                
                if (resource_info['resource_id'] in resource_name or 
                    resource_info['resource_id'] == resource_name):
                    return True
            
            # Check CloudTrail record for resource references
            cloud_trail_event = event.get('CloudTrailEvent')
            if cloud_trail_event:
                try:
                    event_detail = json.loads(cloud_trail_event)
                    event_str = json.dumps(event_detail).lower()
                    
                    # Look for resource ID in the event details
                    if resource_info['resource_id'].lower() in event_str:
                        return True
                        
                except json.JSONDecodeError:
                    pass
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking event relevance: {e}")
            return False
    
    def _process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process and clean up a CloudTrail event"""
        try:
            processed = {
                'event_time': event.get('EventTime', '').isoformat() if event.get('EventTime') else '',
                'event_name': event.get('EventName', ''),
                'event_source': event.get('EventSource', ''),
                'user_name': event.get('Username', ''),
                'source_ip': '',
                'user_agent': '',
                'aws_region': '',
                'error_code': '',
                'error_message': '',
                'resources': [],
                'request_parameters': {},
                'response_elements': {}
            }
            
            # Parse CloudTrail event details
            cloud_trail_event = event.get('CloudTrailEvent')
            if cloud_trail_event:
                try:
                    event_detail = json.loads(cloud_trail_event)
                    
                    processed['source_ip'] = event_detail.get('sourceIPAddress', '')
                    processed['user_agent'] = event_detail.get('userAgent', '')
                    processed['aws_region'] = event_detail.get('awsRegion', '')
                    
                    # Error information
                    if 'errorCode' in event_detail:
                        processed['error_code'] = event_detail['errorCode']
                    if 'errorMessage' in event_detail:
                        processed['error_message'] = event_detail['errorMessage']
                    
                    # Request parameters (sanitized)
                    if 'requestParameters' in event_detail:
                        processed['request_parameters'] = self._sanitize_parameters(
                            event_detail['requestParameters']
                        )
                    
                    # Response elements (sanitized)
                    if 'responseElements' in event_detail:
                        processed['response_elements'] = self._sanitize_parameters(
                            event_detail['responseElements']
                        )
                        
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Error parsing CloudTrail event JSON: {e}")
            
            # Process resources
            for resource in event.get('Resources', []):
                processed['resources'].append({
                    'resource_name': resource.get('ResourceName', ''),
                    'resource_type': resource.get('ResourceType', '')
                })
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Error processing CloudTrail event: {e}")
            return {
                'event_time': '',
                'event_name': event.get('EventName', ''),
                'error': f"Error processing event: {str(e)}"
            }
    
    def _sanitize_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize request/response parameters to remove sensitive data"""
        if not isinstance(params, dict):
            return {}
        
        sanitized = {}
        sensitive_keys = {
            'password', 'secret', 'key', 'token', 'credential', 
            'auth', 'signature', 'private', 'confidential'
        }
        
        for key, value in params.items():
            key_lower = key.lower()
            
            # Check if key contains sensitive information
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_parameters(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_parameters(item) if isinstance(item, dict) else item
                    for item in value[:10]  # Limit list size
                ]
            else:
                # Convert to string and limit length
                str_value = str(value)
                sanitized[key] = str_value[:500] if len(str_value) > 500 else str_value
        
        return sanitized
    
    def _get_resource_metrics(self, resource_info: Dict[str, str], 
                            start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get CloudWatch metrics for the resource during the time period"""
        try:
            service = resource_info['service']
            resource_id = resource_info['resource_id']
            
            metrics = {
                'api_calls': 0,
                'errors': 0,
                'configuration_changes': 0,
                'access_denied': 0
            }
            
            # Service-specific metric collection would go here
            # For now, return basic structure
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting resource metrics: {e}")
            return {}
    
    def _generate_summary(self, results: Dict[str, Any]) -> str:
        """Generate a summary of the CloudTrail collection results"""
        try:
            total_events = results['total_events']
            resource_count = len(results['cloudtrail_data'])
            error_count = len(results['errors'])
            
            summary_parts = [
                f"Collected {total_events} CloudTrail events across {resource_count} resources."
            ]
            
            if error_count > 0:
                summary_parts.append(f"Encountered {error_count} errors during collection.")
            
            # Analyze event patterns
            event_types = {}
            error_events = 0
            config_changes = 0
            
            for resource_data in results['cloudtrail_data']:
                for event in resource_data.get('events', []):
                    event_name = event.get('event_name', 'Unknown')
                    event_types[event_name] = event_types.get(event_name, 0) + 1
                    
                    if event.get('error_code'):
                        error_events += 1
                    
                    # Check for configuration changes
                    if any(keyword in event_name.lower() for keyword in 
                          ['create', 'delete', 'modify', 'update', 'put', 'attach', 'detach']):
                        config_changes += 1
            
            if error_events > 0:
                summary_parts.append(f"Found {error_events} error events.")
            
            if config_changes > 0:
                summary_parts.append(f"Detected {config_changes} configuration changes.")
            
            # Top event types
            if event_types:
                top_events = sorted(event_types.items(), key=lambda x: x[1], reverse=True)[:3]
                top_event_names = [f"{name} ({count})" for name, count in top_events]
                summary_parts.append(f"Top event types: {', '.join(top_event_names)}.")
            
            return ' '.join(summary_parts)
            
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return f"CloudTrail collection completed with {results.get('total_events', 0)} events."
    
    def collect_events_by_time_range(self, start_time: datetime, end_time: datetime,
                                   event_names: List[str] = None,
                                   max_events: int = 100) -> Dict[str, Any]:
        """
        Collect CloudTrail events for a specific time range
        
        Args:
            start_time: Start time for event collection
            end_time: End time for event collection
            event_names: List of specific event names to filter (optional)
            max_events: Maximum number of events to collect
            
        Returns:
            Dictionary containing collected events
        """
        self.logger.info(f"Collecting CloudTrail events from {start_time} to {end_time}")
        
        events = []
        next_token = None
        
        while len(events) < max_events:
            try:
                params = {
                    'StartTime': start_time,
                    'EndTime': end_time,
                    'MaxResults': min(50, max_events - len(events))
                }
                
                if next_token:
                    params['NextToken'] = next_token
                
                response = self.cloudtrail_client.lookup_events(**params)
                
                for event in response.get('Events', []):
                    # Filter by event names if specified
                    if event_names and event.get('EventName') not in event_names:
                        continue
                    
                    processed_event = self._process_event(event)
                    events.append(processed_event)
                
                next_token = response.get('NextToken')
                if not next_token:
                    break
                    
            except Exception as e:
                self.logger.error(f"Error in lookup_events: {e}")
                break
        
        return {
            'events': events[:max_events],
            'event_count': len(events),
            'time_range': {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            },
            'summary': f"Collected {len(events)} events from {start_time} to {end_time}"
        }
