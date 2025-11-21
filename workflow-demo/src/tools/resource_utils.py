"""
Utility functions for resource attribute collection

This module provides convenient functions for collecting resource attributes
that can be used by agents and other components.
"""

import logging
from typing import Dict, List, Any, Optional
from .resource_attributes_collector import ResourceAttributesCollector

def collect_multiple_resource_attributes(resource_arns: List[str], region_name: str = 'us-east-1') -> Dict[str, Any]:
    """
    Collect attributes for multiple resources
    
    Args:
        resource_arns: List of AWS resource ARNs
        region_name: AWS region name
        
    Returns:
        Dictionary containing attributes for all resources
    """
    collector = ResourceAttributesCollector(region_name=region_name)
    results = {
        'ec2_resources': [],
        'lambda_resources': [],
        'dynamodb_resources': [],
        's3_resources': [],
        'rds_resources': [],
        'apigateway_resources': [],
        'elb_resources': [],
        'errors': []
    }
    
    for arn in resource_arns:
        try:
            attributes = collector.collect_resource_attributes(arn)
            
            if 'error' in attributes:
                results['errors'].append({
                    'resource_arn': arn,
                    'error': attributes['error']
                })
                continue
            
            resource_type = attributes.get('resource_type', 'unknown')
            
            if resource_type == 'ec2':
                results['ec2_resources'].append(attributes)
            elif resource_type == 'lambda':
                results['lambda_resources'].append(attributes)
            elif resource_type == 'dynamodb':
                results['dynamodb_resources'].append(attributes)
            elif resource_type == 's3':
                results['s3_resources'].append(attributes)
            elif resource_type == 'rds':
                results['rds_resources'].append(attributes)
            elif resource_type == 'apigateway':
                results['apigateway_resources'].append(attributes)
            elif resource_type == 'elasticloadbalancing':
                results['elb_resources'].append(attributes)
            else:
                results['errors'].append({
                    'resource_arn': arn,
                    'error': f'Unsupported resource type: {resource_type}'
                })
                
        except Exception as e:
            results['errors'].append({
                'resource_arn': arn,
                'error': str(e)
            })
    
    return results

def get_resource_summary(resource_attributes: Dict[str, Any]) -> str:
    """
    Generate a human-readable summary of resource attributes
    
    Args:
        resource_attributes: Resource attributes dictionary
        
    Returns:
        Human-readable summary string
    """
    if 'error' in resource_attributes:
        return f"Error collecting attributes: {resource_attributes['error']}"
    
    resource_type = resource_attributes.get('resource_type', 'unknown')
    attributes = resource_attributes.get('attributes', {})
    
    if resource_type == 'ec2':
        return f"EC2 Instance {attributes.get('instance_id', 'unknown')} ({attributes.get('instance_type', 'unknown')}) - State: {attributes.get('state', 'unknown')}, CPU: {attributes.get('metrics', {}).get('cpu_utilization', 0)}%"
    
    elif resource_type == 'lambda':
        metrics = attributes.get('metrics', {})
        return f"Lambda Function {attributes.get('function_name', 'unknown')} - Success Rate: {metrics.get('success_rate', 0)}%, Throttles: {metrics.get('throttles', 0)}"
    
    elif resource_type == 'dynamodb':
        metrics = attributes.get('metrics', {})
        return f"DynamoDB Table {attributes.get('table_name', 'unknown')} - Status: {attributes.get('table_status', 'unknown')}, Throttles: {metrics.get('throttled_requests', 0)}"
    
    elif resource_type == 's3':
        metrics = attributes.get('metrics', {})
        policy_info = " (with policy)" if attributes.get('has_bucket_policy', False) else " (no policy)"
        return f"S3 Bucket {attributes.get('bucket_name', 'unknown')}{policy_info} - Objects: {metrics.get('number_of_objects', 0)}, Errors: {metrics.get('errors_4xx', 0) + metrics.get('errors_5xx', 0)}"
    
    elif resource_type == 'rds':
        metrics = attributes.get('metrics', {})
        return f"RDS Instance {attributes.get('db_instance_id', 'unknown')} ({attributes.get('engine', 'unknown')}) - Status: {attributes.get('db_instance_status', 'unknown')}, CPU: {metrics.get('cpu_utilization', 0)}%"
    
    elif resource_type == 'apigateway':
        return f"API Gateway {attributes.get('api_name', 'unknown')} - Stages: {len(attributes.get('stages', []))}"
    
    elif resource_type == 'elasticloadbalancing':
        metrics = attributes.get('metrics', {})
        return f"Load Balancer {attributes.get('load_balancer_name', 'unknown')} - State: {attributes.get('state', 'unknown')}, Healthy Hosts: {metrics.get('healthy_host_count', 0)}"
    
    else:
        return f"Unknown resource type: {resource_type}"

def extract_resource_arns_from_text(text: str) -> List[str]:
    """
    Extract AWS resource ARNs from text
    
    Args:
        text: Text that may contain ARNs
        
    Returns:
        List of extracted ARNs
    """
    import re
    
    # Enhanced pattern to match AWS ARNs including function names with colons and hyphens
    # Format: arn:aws:service:region:account:resource-type:resource-name
    arn_pattern = r'arn:aws:[a-zA-Z0-9\-]+:[a-zA-Z0-9\-]*:[0-9]*:[a-zA-Z0-9\-_/:\.]*'
    
    arns = re.findall(arn_pattern, text)
    
    # Filter out any empty or invalid ARNs
    valid_arns = []
    for arn in arns:
        # Basic validation: ARN should have at least 6 parts when split by ':'
        parts = arn.split(':')
        if len(parts) >= 6 and arn.startswith('arn:aws:'):
            valid_arns.append(arn)
    
    return list(set(valid_arns))  # Remove duplicates

def format_resource_collection_for_display(resource_collection: Dict[str, Any]) -> str:
    """
    Format resource collection results for display
    
    Args:
        resource_collection: Resource collection results
        
    Returns:
        Formatted string for display
    """
    output = []
    
    # EC2 Resources
    if resource_collection.get('ec2_resources'):
        output.append("EC2 Instances:")
        for resource in resource_collection['ec2_resources']:
            attrs = resource.get('attributes', {})
            metrics = attrs.get('metrics', {})
            output.append(f"  - {attrs.get('instance_id', 'unknown')} ({attrs.get('instance_type', 'unknown')})")
            output.append(f"    State: {attrs.get('state', 'unknown')}, CPU: {metrics.get('cpu_utilization', 0)}%")
    
    # Lambda Functions
    if resource_collection.get('lambda_resources'):
        output.append("Lambda Functions:")
        for resource in resource_collection['lambda_resources']:
            attrs = resource.get('attributes', {})
            metrics = attrs.get('metrics', {})
            output.append(f"  - {attrs.get('function_name', 'unknown')} ({attrs.get('runtime', 'unknown')})")
            output.append(f"    Success Rate: {metrics.get('success_rate', 0)}%, Throttles: {metrics.get('throttles', 0)}")
    
    # DynamoDB Tables
    if resource_collection.get('dynamodb_resources'):
        output.append("DynamoDB Tables:")
        for resource in resource_collection['dynamodb_resources']:
            attrs = resource.get('attributes', {})
            metrics = attrs.get('metrics', {})
            output.append(f"  - {attrs.get('table_name', 'unknown')}")
            output.append(f"    Status: {attrs.get('table_status', 'unknown')}, Throttles: {metrics.get('throttled_requests', 0)}")
    
    # S3 Buckets
    if resource_collection.get('s3_resources'):
        output.append("S3 Buckets:")
        for resource in resource_collection['s3_resources']:
            attrs = resource.get('attributes', {})
            metrics = attrs.get('metrics', {})
            output.append(f"  - {attrs.get('bucket_name', 'unknown')}")
            output.append(f"    Objects: {metrics.get('number_of_objects', 0)}, Errors: {metrics.get('errors_4xx', 0) + metrics.get('errors_5xx', 0)}")
            
            # Add bucket policy information
            if attrs.get('has_bucket_policy', False):
                policy_length = attrs.get('bucket_policy_length', 0)
                output.append(f"    Bucket Policy: Present ({policy_length} characters)")
                
                # If we have the parsed policy, show key details
                bucket_policy = attrs.get('bucket_policy')
                if bucket_policy:
                    statements = bucket_policy.get('Statement', [])
                    output.append(f"    Policy Statements: {len(statements)}")
                    
                    # Show principal types and effects
                    principals = set()
                    effects = set()
                    actions = set()
                    resources = set()
                    
                    for stmt in statements:
                        if 'Principal' in stmt:
                            principal = stmt['Principal']
                            if isinstance(principal, dict):
                                for key, value in principal.items():
                                    if isinstance(value, list):
                                        for v in value:
                                            principals.add(f"{key}:{v}")
                                    else:
                                        principals.add(f"{key}:{value}")
                            elif isinstance(principal, str):
                                principals.add(principal)
                        
                        if 'Effect' in stmt:
                            effects.add(stmt['Effect'])
                            
                        if 'Action' in stmt:
                            if isinstance(stmt['Action'], list):
                                actions.update(stmt['Action'])
                            else:
                                actions.add(stmt['Action'])
                                
                        if 'Resource' in stmt:
                            if isinstance(stmt['Resource'], list):
                                resources.update(stmt['Resource'])
                            else:
                                resources.add(stmt['Resource'])
                    
                    if principals:
                        output.append(f"    Principals: {', '.join(principals)}")
                    if effects:
                        output.append(f"    Effects: {', '.join(effects)}")
                    if actions:
                        output.append(f"    Actions: {', '.join(actions)}")
                    if resources:
                        output.append(f"    Resources: {', '.join(resources)}")
                    
                    # Add full policy for reference
                    import json
                    output.append(f"    Full Policy: {json.dumps(bucket_policy, indent=2)}")
            else:
                output.append(f"    Bucket Policy: None")
            
            # Add versioning status
            versioning = attrs.get('versioning_status', 'Unknown')
            output.append(f"    Versioning: {versioning}")
    
    # RDS Instances
    if resource_collection.get('rds_resources'):
        output.append("RDS Instances:")
        for resource in resource_collection['rds_resources']:
            attrs = resource.get('attributes', {})
            metrics = attrs.get('metrics', {})
            output.append(f"  - {attrs.get('db_instance_id', 'unknown')} ({attrs.get('engine', 'unknown')})")
            output.append(f"    Status: {attrs.get('db_instance_status', 'unknown')}, CPU: {metrics.get('cpu_utilization', 0)}%")
    
    # API Gateway
    if resource_collection.get('apigateway_resources'):
        output.append("API Gateways:")
        for resource in resource_collection['apigateway_resources']:
            attrs = resource.get('attributes', {})
            output.append(f"  - {attrs.get('api_name', 'unknown')} (ID: {attrs.get('api_id', 'unknown')})")
            output.append(f"    Stages: {len(attrs.get('stages', []))}")
    
    # Load Balancers
    if resource_collection.get('elb_resources'):
        output.append("Load Balancers:")
        for resource in resource_collection['elb_resources']:
            attrs = resource.get('attributes', {})
            metrics = attrs.get('metrics', {})
            output.append(f"  - {attrs.get('load_balancer_name', 'unknown')} ({attrs.get('load_balancer_type', 'unknown')})")
            output.append(f"    State: {attrs.get('state', 'unknown')}, Healthy Hosts: {metrics.get('healthy_host_count', 0)}")
    
    # Errors
    if resource_collection.get('errors'):
        output.append("Errors:")
        for error in resource_collection['errors']:
            output.append(f"  - {error.get('resource_arn', 'unknown')}: {error.get('error', 'unknown error')}")
    
    return "\n".join(output) if output else "No resources found or collected."
