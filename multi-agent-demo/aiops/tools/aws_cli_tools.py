"""AWS CLI tools for resource information and configuration."""

import boto3
from typing import Dict, Any, Optional
from strands.tools import tool

@tool
def get_resource_info(service: str, operation: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute AWS CLI command to get resource information.
    
    Args:
        service: AWS service name (e.g., 'ec2', 'rds', 's3')
        operation: Operation name in snake_case (e.g., 'describe_instances', 'describe_db_instances')
        parameters: Operation parameters as key-value pairs
        
    Returns:
        Dict containing the AWS API response
        
    Example:
        get_resource_info('ec2', 'describe_instances', {'InstanceIds': ['i-1234567890abcdef0']})
    """
    try:
        if parameters is None:
            parameters = {}
            
        client = boto3.client(service)
        method = getattr(client, operation)
        result = method(**parameters)
        
        if 'ResponseMetadata' in result:
            del result['ResponseMetadata']
        
        return result
        
    except Exception as e:
        return {'error': str(e)}


@tool
def get_resource_config(service: str, operation: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute AWS CLI command to get resource configuration details.
    
    Args:
        service: AWS service name (e.g., 'ec2', 'rds', 'elbv2')
        operation: Operation name in snake_case (e.g., 'describe_instances', 'describe_load_balancers')
        parameters: Operation parameters as key-value pairs
        
    Returns:
        Dict containing the AWS API response with configuration details
        
    Example:
        get_resource_config('rds', 'describe_db_instances', {'DBInstanceIdentifier': 'mydb'})
    """
    try:
        if parameters is None:
            parameters = {}
            
        client = boto3.client(service)
        method = getattr(client, operation)
        result = method(**parameters)
        
        if 'ResponseMetadata' in result:
            del result['ResponseMetadata']
        
        return result
        
    except Exception as e:
        return {'error': str(e)}
