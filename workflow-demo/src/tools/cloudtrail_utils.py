"""
Utility functions for CloudTrail collection

This module provides convenient functions for collecting CloudTrail events
that can be used by agents and other components.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .cloudtrail_collector import CloudTrailCollector

def collect_events_for_incident(resource_arns: List[str], 
                               alarm_timestamp: datetime = None,
                               region_name: str = 'us-east-1') -> Dict[str, Any]:
    """
    Collect CloudTrail events for an incident
    
    Args:
        resource_arns: List of AWS resource ARNs involved in the incident
        alarm_timestamp: Timestamp when the alarm was triggered
        region_name: AWS region name
        
    Returns:
        Dictionary containing CloudTrail analysis results
    """
    if not alarm_timestamp:
        alarm_timestamp = datetime.utcnow()
    
    # Look for events from 10 minutes before alarm to now
    start_time = alarm_timestamp - timedelta(minutes=10)
    end_time = datetime.utcnow()
    
    collector = CloudTrailCollector(region_name=region_name)
    
    try:
        results = collector.collect_events_for_resources(
            resource_arns=resource_arns,
            start_time=start_time,
            end_time=end_time,
            max_events=50  # Reasonable limit for incident analysis
        )
        
        # Add incident-specific analysis
        results['incident_analysis'] = analyze_incident_events(results)
        
        return results
        
    except Exception as e:
        logging.error(f"Error collecting events for incident: {e}")
        return {
            'cloudtrail_data': [],
            'summary': f'Error collecting CloudTrail events: {str(e)}',
            'total_events': 0,
            'errors': [{'error': str(e)}],
            'incident_analysis': {}
        }

def analyze_incident_events(cloudtrail_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze CloudTrail events for incident patterns
    
    Args:
        cloudtrail_results: Results from CloudTrail collection
        
    Returns:
        Dictionary containing incident analysis
    """
    analysis = {
        'configuration_changes': [],
        'error_events': [],
        'suspicious_activities': [],
        'timeline': [],
        'affected_users': set(),
        'affected_services': set()
    }
    
    try:
        for resource_data in cloudtrail_results.get('cloudtrail_data', []):
            resource_name = resource_data.get('resource_name', 'unknown')
            
            for event in resource_data.get('events', []):
                event_time = event.get('event_time', '')
                event_name = event.get('event_name', '')
                user_name = event.get('user_name', '')
                error_code = event.get('error_code', '')
                
                # Track users and services
                if user_name:
                    analysis['affected_users'].add(user_name)
                
                service = event.get('event_source', '').replace('.amazonaws.com', '')
                if service:
                    analysis['affected_services'].add(service)
                
                # Identify configuration changes
                if any(keyword in event_name.lower() for keyword in 
                      ['create', 'delete', 'modify', 'update', 'put', 'attach', 'detach']):
                    analysis['configuration_changes'].append({
                        'resource': resource_name,
                        'event_name': event_name,
                        'event_time': event_time,
                        'user': user_name,
                        'details': event.get('request_parameters', {})
                    })
                
                # Identify error events
                if error_code:
                    analysis['error_events'].append({
                        'resource': resource_name,
                        'event_name': event_name,
                        'event_time': event_time,
                        'error_code': error_code,
                        'error_message': event.get('error_message', ''),
                        'user': user_name
                    })
                
                # Identify suspicious activities
                if any(keyword in event_name.lower() for keyword in 
                      ['assume', 'escalate', 'privilege', 'policy']):
                    analysis['suspicious_activities'].append({
                        'resource': resource_name,
                        'event_name': event_name,
                        'event_time': event_time,
                        'user': user_name,
                        'source_ip': event.get('source_ip', '')
                    })
                
                # Build timeline
                analysis['timeline'].append({
                    'time': event_time,
                    'resource': resource_name,
                    'event': event_name,
                    'user': user_name,
                    'status': 'error' if error_code else 'success'
                })
        
        # Convert sets to lists for JSON serialization
        analysis['affected_users'] = list(analysis['affected_users'])
        analysis['affected_services'] = list(analysis['affected_services'])
        
        # Sort timeline by time
        analysis['timeline'].sort(key=lambda x: x['time'])
        
        return analysis
        
    except Exception as e:
        logging.error(f"Error analyzing incident events: {e}")
        return analysis

def construct_arn_from_resource(resource_id: str, resource_type: str, context: Dict[str, Any]) -> str:
    """
    Construct ARN from resource ID and type
    
    Args:
        resource_id: The resource identifier
        resource_type: The AWS resource type
        context: Context containing account and region info
        
    Returns:
        Constructed ARN string or empty string if unable to construct
    """
    try:
        # Get account and region from context
        account_id = context.get('account_id', '')
        region = context.get('region', '')
        
        # Try to get from alarm analysis if not in root context
        if not account_id or not region:
            alarm_analysis = context.get('alarm_analysis', {})
            if isinstance(alarm_analysis, dict):
                extracted_info = alarm_analysis.get('extracted_info', {})
                if isinstance(extracted_info, dict):
                    account_id = account_id or extracted_info.get('account_id', '')
                    region = region or extracted_info.get('region', '')
        
        if not account_id or not region:
            return ''
        
        # Construct ARN based on resource type
        if resource_type == 'AWS::Lambda::Function':
            return f"arn:aws:lambda:{region}:{account_id}:function:{resource_id}"
        elif resource_type == 'AWS::S3::Bucket':
            return f"arn:aws:s3:::{resource_id}"
        elif resource_type == 'AWS::EC2::Instance':
            return f"arn:aws:ec2:{region}:{account_id}:instance/{resource_id}"
        elif resource_type == 'AWS::RDS::DBInstance':
            return f"arn:aws:rds:{region}:{account_id}:db:{resource_id}"
        elif resource_type == 'AWS::ApiGateway::RestApi':
            return f"arn:aws:apigateway:{region}::/restapis/{resource_id}"
        elif resource_type == 'AWS::DynamoDB::Table':
            return f"arn:aws:dynamodb:{region}:{account_id}:table/{resource_id}"
        else:
            # For unknown types, return empty string
            return ''
            
    except Exception as e:
        logging.error(f"Error constructing ARN for {resource_id} ({resource_type}): {e}")
        return ''

def extract_resource_arns_from_context(context: Dict[str, Any]) -> List[str]:
    """
    Extract resource ARNs from workflow context
    
    Args:
        context: Workflow context containing resource information
        
    Returns:
        List of resource ARNs
    """
    resource_arns = []
    
    try:
        # Check alarm analysis for resources
        alarm_analysis = context.get('alarm_analysis', {})
        if isinstance(alarm_analysis, dict):
            alarm_arn = alarm_analysis.get('alarm_arn', '')
            if alarm_arn:
                resource_arns.append(alarm_arn)
        
        # Check trace analysis for resources
        trace_analysis = context.get('trace_analysis', {})
        if isinstance(trace_analysis, dict):
            relevant_resources = trace_analysis.get('relevant_resources', [])
            if isinstance(relevant_resources, list):
                for resource in relevant_resources:
                    if isinstance(resource, dict):
                        # Extract ARN from resource object
                        resource_id = resource.get('resource_id', '')
                        resource_type = resource.get('resource_type', '')
                        
                        # Try to construct ARN based on resource type
                        if resource_id and resource_type:
                            arn = construct_arn_from_resource(resource_id, resource_type, context)
                            if arn:
                                resource_arns.append(arn)
                    elif isinstance(resource, str):
                        # If it's already a string (ARN), use it directly
                        resource_arns.append(resource)
        
        # Check resource collection for resources
        resource_collection = context.get('resource_collection', {})
        if isinstance(resource_collection, dict):
            for resource_type in ['ec2_resources', 'lambda_resources', 's3_resources', 
                                'rds_resources', 'apigateway_resources', 'dynamodb_resources']:
                resources = resource_collection.get(resource_type, [])
                for resource in resources:
                    if isinstance(resource, dict):
                        arn = resource.get('resource_arn', '')
                        if arn:
                            resource_arns.append(arn)
        
        # Remove duplicates and filter out empty strings
        resource_arns = [arn for arn in resource_arns if arn and isinstance(arn, str)]
        resource_arns = list(set(resource_arns))
        
        return resource_arns
        
    except Exception as e:
        logging.error(f"Error extracting resource ARNs from context: {e}")
        return []

def format_cloudtrail_analysis_for_display(cloudtrail_results: Dict[str, Any]) -> str:
    """
    Format CloudTrail analysis results for display
    
    Args:
        cloudtrail_results: CloudTrail collection results
        
    Returns:
        Formatted string for display
    """
    try:
        output = []
        
        # Summary
        summary = cloudtrail_results.get('summary', '')
        if summary:
            output.append(f"Summary: {summary}")
            output.append("")
        
        # Resource events
        cloudtrail_data = cloudtrail_results.get('cloudtrail_data', [])
        if cloudtrail_data:
            output.append("CloudTrail Events by Resource:")
            
            for resource_data in cloudtrail_data:
                resource_name = resource_data.get('resource_name', 'unknown')
                event_count = resource_data.get('event_count', 0)
                
                output.append(f"  • {resource_name}: {event_count} events")
                
                # Show recent events
                events = resource_data.get('events', [])[:5]  # Show first 5 events
                for event in events:
                    event_time = event.get('event_time', '')[:19]  # Remove microseconds
                    event_name = event.get('event_name', '')
                    user_name = event.get('user_name', 'unknown')
                    error_code = event.get('error_code', '')
                    
                    status = f" [ERROR: {error_code}]" if error_code else ""
                    output.append(f"    - {event_time}: {event_name} by {user_name}{status}")
                
                if len(resource_data.get('events', [])) > 5:
                    remaining = len(resource_data.get('events', [])) - 5
                    output.append(f"    ... and {remaining} more events")
                
                output.append("")
        
        # Incident analysis
        incident_analysis = cloudtrail_results.get('incident_analysis', {})
        if incident_analysis:
            config_changes = incident_analysis.get('configuration_changes', [])
            if config_changes:
                output.append(f"Configuration Changes ({len(config_changes)}):")
                for change in config_changes[:3]:  # Show first 3
                    output.append(f"  • {change.get('event_name', '')} on {change.get('resource', '')} by {change.get('user', '')}")
                if len(config_changes) > 3:
                    output.append(f"  ... and {len(config_changes) - 3} more changes")
                output.append("")
            
            error_events = incident_analysis.get('error_events', [])
            if error_events:
                output.append(f"Error Events ({len(error_events)}):")
                for error in error_events[:3]:  # Show first 3
                    output.append(f"  • {error.get('error_code', '')}: {error.get('event_name', '')} on {error.get('resource', '')}")
                if len(error_events) > 3:
                    output.append(f"  ... and {len(error_events) - 3} more errors")
                output.append("")
            
            affected_users = incident_analysis.get('affected_users', [])
            if affected_users:
                output.append(f"Affected Users: {', '.join(affected_users[:5])}")
                if len(affected_users) > 5:
                    output.append(f" ... and {len(affected_users) - 5} more")
                output.append("")
            
            affected_services = incident_analysis.get('affected_services', [])
            if affected_services:
                output.append(f"Affected Services: {', '.join(affected_services)}")
                output.append("")
        
        # Errors
        errors = cloudtrail_results.get('errors', [])
        if errors:
            output.append("Collection Errors:")
            for error in errors:
                output.append(f"  • {error.get('resource_arn', 'unknown')}: {error.get('error', '')}")
        
        return "\n".join(output) if output else "No CloudTrail data collected."
        
    except Exception as e:
        logging.error(f"Error formatting CloudTrail analysis: {e}")
        return f"Error formatting CloudTrail analysis: {str(e)}"

def generate_cloudtrail_recommendations(cloudtrail_results: Dict[str, Any]) -> List[str]:
    """
    Generate recommendations based on CloudTrail analysis
    
    Args:
        cloudtrail_results: CloudTrail collection results
        
    Returns:
        List of recommendations
    """
    recommendations = []
    
    try:
        incident_analysis = cloudtrail_results.get('incident_analysis', {})
        
        # Configuration change recommendations
        config_changes = incident_analysis.get('configuration_changes', [])
        if len(config_changes) > 5:
            recommendations.append(f"High number of configuration changes ({len(config_changes)}) detected. Review change management processes.")
        
        # Error event recommendations
        error_events = incident_analysis.get('error_events', [])
        if len(error_events) > 3:
            recommendations.append(f"Multiple error events ({len(error_events)}) found. Investigate permission issues and API failures.")
        
        # User activity recommendations
        affected_users = incident_analysis.get('affected_users', [])
        if len(affected_users) > 10:
            recommendations.append(f"Many users ({len(affected_users)}) involved in incident. Review access patterns and potential security issues.")
        
        # Service recommendations
        affected_services = incident_analysis.get('affected_services', [])
        if len(affected_services) > 5:
            recommendations.append(f"Multiple services ({len(affected_services)}) affected. Consider cross-service dependencies and cascading failures.")
        
        # Suspicious activity recommendations
        suspicious_activities = incident_analysis.get('suspicious_activities', [])
        if suspicious_activities:
            recommendations.append(f"Suspicious activities detected ({len(suspicious_activities)}). Review security logs and access patterns.")
        
        # General recommendations
        total_events = cloudtrail_results.get('total_events', 0)
        if total_events == 0:
            recommendations.append("No CloudTrail events found. Verify CloudTrail is enabled and configured properly.")
        elif total_events > 100:
            recommendations.append("High volume of CloudTrail events. Consider filtering and focusing on critical events.")
        
        return recommendations
        
    except Exception as e:
        logging.error(f"Error generating CloudTrail recommendations: {e}")
        return [f"Error generating recommendations: {str(e)}"]
