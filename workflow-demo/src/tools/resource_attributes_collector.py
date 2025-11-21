"""
AWS Resource Attributes Collector Tool

This tool provides comprehensive methods to collect detailed attributes and metrics
for various AWS resources including EC2, Lambda, DynamoDB, S3, RDS, API Gateway, etc.

The tool integrates with AWS APIs to gather real-time resource information and metrics
that can be used for troubleshooting, monitoring, and root cause analysis.
"""

import boto3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError, NoCredentialsError

from .resource_collectors import AdditionalResourceCollectors

class ResourceAttributesCollector(AdditionalResourceCollectors):
    """Main class for collecting AWS resource attributes and metrics"""
    
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize the resource attributes collector
        
        Args:
            region_name: AWS region to use for API calls
        """
        self.region_name = region_name
        self.logger = logging.getLogger(__name__)
        
        # Initialize AWS clients
        try:
            self.ec2_client = boto3.client('ec2', region_name=region_name)
            self.cloudwatch_client = boto3.client('cloudwatch', region_name=region_name)
            self.lambda_client = boto3.client('lambda', region_name=region_name)
            self.dynamodb_client = boto3.client('dynamodb', region_name=region_name)
            self.s3_client = boto3.client('s3', region_name=region_name)
            self.rds_client = boto3.client('rds', region_name=region_name)
            self.apigateway_client = boto3.client('apigateway', region_name=region_name)
            self.elbv2_client = boto3.client('elbv2', region_name=region_name)
            
            self.logger.info(f"Initialized AWS clients for region: {region_name}")
            
        except NoCredentialsError:
            self.logger.error("AWS credentials not found. Please configure AWS credentials.")
            raise
        except Exception as e:
            self.logger.error(f"Error initializing AWS clients: {e}")
            raise
    
    def collect_resource_attributes(self, resource_arn: str) -> Dict[str, Any]:
        """
        Collect attributes for a resource based on its ARN
        
        Args:
            resource_arn: AWS resource ARN
            
        Returns:
            Dictionary containing resource attributes and metrics
        """
        try:
            # Parse resource type from ARN
            resource_type = self._parse_resource_type(resource_arn)
            
            if resource_type == 'ec2':
                return self.get_ec2_attributes(resource_arn)
            elif resource_type == 'lambda':
                return self.get_lambda_attributes(resource_arn)
            elif resource_type == 'dynamodb':
                return self.get_dynamodb_attributes(resource_arn)
            elif resource_type == 's3':
                return self.get_s3_attributes(resource_arn)
            elif resource_type == 'rds':
                return self.get_rds_attributes(resource_arn)
            elif resource_type == 'apigateway':
                return self.get_apigateway_attributes(resource_arn)
            elif resource_type == 'elasticloadbalancing':
                return self.get_elb_attributes(resource_arn)
            else:
                return {
                    'resource_arn': resource_arn,
                    'resource_type': resource_type,
                    'error': f'Unsupported resource type: {resource_type}',
                    'attributes': {}
                }
                
        except Exception as e:
            self.logger.error(f"Error collecting attributes for {resource_arn}: {e}")
            return {
                'resource_arn': resource_arn,
                'error': str(e),
                'attributes': {}
            }
    
    def _parse_resource_type(self, resource_arn: str) -> str:
        """Parse resource type from ARN"""
        try:
            # ARN format: arn:aws:service:region:account:resource
            parts = resource_arn.split(':')
            if len(parts) >= 3:
                return parts[2]  # service name
            return 'unknown'
        except Exception:
            return 'unknown'
    
    def _get_cloudwatch_metrics(self, namespace: str, metric_name: str, 
                               dimensions: List[Dict], start_time: datetime = None,
                               end_time: datetime = None, period: int = 300) -> float:
        """
        Get CloudWatch metric value
        
        Args:
            namespace: CloudWatch namespace
            metric_name: Metric name
            dimensions: Metric dimensions
            start_time: Start time for metric query
            end_time: End time for metric query
            period: Period in seconds
            
        Returns:
            Latest metric value or 0 if not available
        """
        try:
            if not start_time:
                start_time = datetime.utcnow() - timedelta(minutes=10)
            if not end_time:
                end_time = datetime.utcnow()
            
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                # Return the most recent datapoint
                latest = max(response['Datapoints'], key=lambda x: x['Timestamp'])
                return latest['Average']
            
            return 0.0
            
        except Exception as e:
            self.logger.warning(f"Error getting CloudWatch metric {metric_name}: {e}")
            return 0.0
    
    def get_ec2_attributes(self, resource_arn: str) -> Dict[str, Any]:
        """
        Get EC2 instance attributes and metrics
        
        Args:
            resource_arn: EC2 instance ARN
            
        Returns:
            Dictionary containing EC2 attributes and metrics
        """
        try:
            # Extract instance ID from ARN
            instance_id = resource_arn.split('/')[-1]
            
            # Get instance details
            response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
            
            if not response['Reservations']:
                return {
                    'resource_arn': resource_arn,
                    'error': f'Instance {instance_id} not found',
                    'attributes': {}
                }
            
            instance = response['Reservations'][0]['Instances'][0]
            
            # Get CloudWatch metrics
            dimensions = [{'Name': 'InstanceId', 'Value': instance_id}]
            
            cpu_utilization = self._get_cloudwatch_metrics(
                'AWS/EC2', 'CPUUtilization', dimensions
            )
            
            network_in = self._get_cloudwatch_metrics(
                'AWS/EC2', 'NetworkIn', dimensions
            )
            
            network_out = self._get_cloudwatch_metrics(
                'AWS/EC2', 'NetworkOut', dimensions
            )
            
            disk_read_ops = self._get_cloudwatch_metrics(
                'AWS/EC2', 'DiskReadOps', dimensions
            )
            
            disk_write_ops = self._get_cloudwatch_metrics(
                'AWS/EC2', 'DiskWriteOps', dimensions
            )
            
            # Get status checks
            status_response = self.ec2_client.describe_instance_status(
                InstanceIds=[instance_id]
            )
            
            instance_status = 'unknown'
            system_status = 'unknown'
            
            if status_response['InstanceStatuses']:
                status = status_response['InstanceStatuses'][0]
                instance_status = status['InstanceStatus']['Status']
                system_status = status['SystemStatus']['Status']
            
            return {
                'resource_arn': resource_arn,
                'resource_type': 'ec2',
                'attributes': {
                    'instance_id': instance_id,
                    'instance_type': instance.get('InstanceType', 'unknown'),
                    'state': instance.get('State', {}).get('Name', 'unknown'),
                    'availability_zone': instance.get('Placement', {}).get('AvailabilityZone', 'unknown'),
                    'launch_time': instance.get('LaunchTime', '').isoformat() if instance.get('LaunchTime') else '',
                    'platform': instance.get('Platform', 'linux'),
                    'vpc_id': instance.get('VpcId', ''),
                    'subnet_id': instance.get('SubnetId', ''),
                    'private_ip': instance.get('PrivateIpAddress', ''),
                    'public_ip': instance.get('PublicIpAddress', ''),
                    'security_groups': [sg['GroupName'] for sg in instance.get('SecurityGroups', [])],
                    'instance_status': instance_status,
                    'system_status': system_status,
                    'metrics': {
                        'cpu_utilization': round(cpu_utilization, 2),
                        'network_in_bytes': int(network_in),
                        'network_out_bytes': int(network_out),
                        'disk_read_ops': int(disk_read_ops),
                        'disk_write_ops': int(disk_write_ops)
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting EC2 attributes for {resource_arn}: {e}")
            return {
                'resource_arn': resource_arn,
                'resource_type': 'ec2',
                'error': str(e),
                'attributes': {}
            }
    
    def get_lambda_attributes(self, resource_arn: str) -> Dict[str, Any]:
        """
        Get Lambda function attributes and metrics
        
        Args:
            resource_arn: Lambda function ARN
            
        Returns:
            Dictionary containing Lambda attributes and metrics
        """
        try:
            self.logger.info(f"Processing Lambda ARN: {resource_arn}")
            
            # Extract function name from ARN
            function_name = resource_arn.split(':')[-1]
            self.logger.info(f"Extracted function name: {function_name}")
            
            # Validate ARN format
            arn_parts = resource_arn.split(':')
            if len(arn_parts) < 7:
                raise ValueError(f"Invalid Lambda ARN format: {resource_arn}")
            
            # Get function configuration
            self.logger.info(f"Calling GetFunction with FunctionName: {function_name}")
            response = self.lambda_client.get_function(FunctionName=function_name)
            config = response['Configuration']
            
            # Get CloudWatch metrics
            dimensions = [{'Name': 'FunctionName', 'Value': function_name}]
            
            invocations = self._get_cloudwatch_metrics(
                'AWS/Lambda', 'Invocations', dimensions
            )
            
            errors = self._get_cloudwatch_metrics(
                'AWS/Lambda', 'Errors', dimensions
            )
            
            duration = self._get_cloudwatch_metrics(
                'AWS/Lambda', 'Duration', dimensions
            )
            
            throttles = self._get_cloudwatch_metrics(
                'AWS/Lambda', 'Throttles', dimensions
            )
            
            concurrent_executions = self._get_cloudwatch_metrics(
                'AWS/Lambda', 'ConcurrentExecutions', dimensions
            )
            
            # Calculate success rate
            success_rate = 0.0
            if invocations > 0:
                success_rate = ((invocations - errors) / invocations) * 100
            
            return {
                'resource_arn': resource_arn,
                'resource_type': 'lambda',
                'attributes': {
                    'function_name': config.get('FunctionName', ''),
                    'runtime': config.get('Runtime', ''),
                    'handler': config.get('Handler', ''),
                    'memory_size': config.get('MemorySize', 0),
                    'timeout': config.get('Timeout', 0),
                    'last_modified': config.get('LastModified', ''),
                    'code_size': config.get('CodeSize', 0),
                    'state': config.get('State', 'unknown'),
                    'version': config.get('Version', ''),
                    'environment_variables': len(config.get('Environment', {}).get('Variables', {})),
                    'layers': len(config.get('Layers', [])),
                    'metrics': {
                        'invocations': int(invocations),
                        'errors': int(errors),
                        'success_rate': round(success_rate, 2),
                        'duration_avg_ms': round(duration, 2),
                        'throttles': int(throttles),
                        'concurrent_executions': int(concurrent_executions)
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting Lambda attributes for {resource_arn}: {e}")
            return {
                'resource_arn': resource_arn,
                'resource_type': 'lambda',
                'error': str(e),
                'attributes': {}
            }
    def get_dynamodb_attributes(self, resource_arn: str) -> Dict[str, Any]:
        """
        Get DynamoDB table attributes and metrics
        
        Args:
            resource_arn: DynamoDB table ARN
            
        Returns:
            Dictionary containing DynamoDB attributes and metrics
        """
        try:
            # Extract table name from ARN
            # ARN format: arn:aws:dynamodb:region:account:table/table-name
            table_name = resource_arn.split('/')[-1]
            
            # Get table description
            response = self.dynamodb_client.describe_table(TableName=table_name)
            table = response['Table']
            
            # Get CloudWatch metrics
            dimensions = [{'Name': 'TableName', 'Value': table_name}]
            
            consumed_read_capacity = self._get_cloudwatch_metrics(
                'AWS/DynamoDB', 'ConsumedReadCapacityUnits', dimensions
            )
            
            consumed_write_capacity = self._get_cloudwatch_metrics(
                'AWS/DynamoDB', 'ConsumedWriteCapacityUnits', dimensions
            )
            
            throttled_requests = self._get_cloudwatch_metrics(
                'AWS/DynamoDB', 'ThrottledRequests', dimensions
            )
            
            return {
                'resource_arn': resource_arn,
                'resource_type': 'dynamodb',
                'attributes': {
                    'table_name': table.get('TableName', ''),
                    'table_status': table.get('TableStatus', ''),
                    'billing_mode': table.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED'),
                    'item_count': table.get('ItemCount', 0),
                    'table_size_bytes': table.get('TableSizeBytes', 0),
                    'provisioned_throughput': {
                        'read_capacity_units': table.get('ProvisionedThroughput', {}).get('ReadCapacityUnits', 0),
                        'write_capacity_units': table.get('ProvisionedThroughput', {}).get('WriteCapacityUnits', 0)
                    },
                    'global_secondary_indexes': len(table.get('GlobalSecondaryIndexes', [])),
                    'local_secondary_indexes': len(table.get('LocalSecondaryIndexes', [])),
                    'metrics': {
                        'consumed_read_capacity': consumed_read_capacity,
                        'consumed_write_capacity': consumed_write_capacity,
                        'throttled_requests': int(throttled_requests)
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting DynamoDB attributes for {resource_arn}: {e}")
            return {
                'resource_arn': resource_arn,
                'resource_type': 'dynamodb',
                'error': str(e),
                'attributes': {}
            }
    
    def get_s3_attributes(self, resource_arn: str) -> Dict[str, Any]:
        """
        Get S3 bucket attributes and metrics
        
        Args:
            resource_arn: S3 bucket ARN
            
        Returns:
            Dictionary containing S3 attributes and metrics
        """
        try:
            # Extract bucket name from ARN
            # ARN format: arn:aws:s3:::bucket-name
            parts = resource_arn.split(':')
            if len(parts) >= 6:
                bucket_name = parts[5]
            else:
                # Handle case where ARN might be malformed or just the bucket name
                bucket_name = resource_arn.split('/')[-1]
                
            # Remove any leading/trailing colons
            bucket_name = bucket_name.strip(':')
            
            self.logger.info(f"Extracted bucket name '{bucket_name}' from ARN: {resource_arn}")
            
            # Get bucket location
            try:
                location_response = self.s3_client.get_bucket_location(Bucket=bucket_name)
                bucket_region = location_response.get('LocationConstraint') or 'us-east-1'
            except Exception as e:
                self.logger.warning(f"Error getting bucket location: {e}")
                bucket_region = 'unknown'
            
            # Get bucket versioning
            try:
                versioning_response = self.s3_client.get_bucket_versioning(Bucket=bucket_name)
                versioning_status = versioning_response.get('Status', 'Disabled')
            except Exception as e:
                self.logger.warning(f"Error getting bucket versioning: {e}")
                versioning_status = 'unknown'
            
            # Get bucket policy (if exists)
            has_bucket_policy = False
            bucket_policy = None
            bucket_policy_json = None
            bucket_policy_length = 0
            
            try:
                policy_response = self.s3_client.get_bucket_policy(Bucket=bucket_name)
                bucket_policy = policy_response.get('Policy', '')
                has_bucket_policy = bool(bucket_policy)
                bucket_policy_length = len(bucket_policy) if bucket_policy else 0
                
                if bucket_policy:
                    # Parse the policy JSON for analysis
                    import json
                    try:
                        bucket_policy_json = json.loads(bucket_policy)
                        self.logger.info(f"Successfully parsed bucket policy for {bucket_name}")
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Invalid JSON in bucket policy: {e}")
                        bucket_policy_json = None
            except Exception as e:
                self.logger.info(f"No bucket policy found or error: {e}")
                has_bucket_policy = False
                bucket_policy = None
                bucket_policy_json = None
            
            # Get CloudWatch metrics
            dimensions = [{'Name': 'BucketName', 'Value': bucket_name}, {'Name': 'StorageType', 'Value': 'StandardStorage'}]
            
            bucket_size = self._get_cloudwatch_metrics(
                'AWS/S3', 'BucketSizeBytes', dimensions
            )
            
            number_of_objects = self._get_cloudwatch_metrics(
                'AWS/S3', 'NumberOfObjects', dimensions
            )
            
            # Get error metrics if available
            errors_4xx = self._get_cloudwatch_metrics(
                'AWS/S3', '4xxErrors', [{'Name': 'BucketName', 'Value': bucket_name}]
            )
            
            errors_5xx = self._get_cloudwatch_metrics(
                'AWS/S3', '5xxErrors', [{'Name': 'BucketName', 'Value': bucket_name}]
            )
            
            return {
                'resource_arn': resource_arn,
                'resource_type': 's3',
                'attributes': {
                    'bucket_name': bucket_name,
                    'bucket_region': bucket_region,
                    'versioning_status': versioning_status,
                    'has_bucket_policy': has_bucket_policy,
                    'bucket_policy_length': bucket_policy_length,
                    'bucket_policy': bucket_policy_json,
                    'bucket_policy_raw': bucket_policy,
                    'metrics': {
                        'bucket_size_bytes': int(bucket_size),
                        'number_of_objects': int(number_of_objects),
                        'errors_4xx': int(errors_4xx),
                        'errors_5xx': int(errors_5xx)
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting S3 attributes for {resource_arn}: {e}")
            return {
                'resource_arn': resource_arn,
                'resource_type': 's3',
                'error': str(e),
                'attributes': {}
            }
    
    def get_rds_attributes(self, resource_arn: str) -> Dict[str, Any]:
        """
        Get RDS instance attributes and metrics
        
        Args:
            resource_arn: RDS instance ARN
            
        Returns:
            Dictionary containing RDS attributes and metrics
        """
        try:
            # Extract DB instance identifier from ARN
            # ARN format: arn:aws:rds:region:account:db:db-instance-id
            db_instance_id = resource_arn.split(':')[-1]
            
            # Get DB instance details
            response = self.rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_id)
            db_instance = response['DBInstances'][0]
            
            # Get CloudWatch metrics
            dimensions = [{'Name': 'DBInstanceIdentifier', 'Value': db_instance_id}]
            
            cpu_utilization = self._get_cloudwatch_metrics(
                'AWS/RDS', 'CPUUtilization', dimensions
            )
            
            database_connections = self._get_cloudwatch_metrics(
                'AWS/RDS', 'DatabaseConnections', dimensions
            )
            
            return {
                'resource_arn': resource_arn,
                'resource_type': 'rds',
                'attributes': {
                    'db_instance_id': db_instance.get('DBInstanceIdentifier', ''),
                    'db_instance_class': db_instance.get('DBInstanceClass', ''),
                    'engine': db_instance.get('Engine', ''),
                    'engine_version': db_instance.get('EngineVersion', ''),
                    'db_instance_status': db_instance.get('DBInstanceStatus', ''),
                    'allocated_storage': db_instance.get('AllocatedStorage', 0),
                    'multi_az': db_instance.get('MultiAZ', False),
                    'metrics': {
                        'cpu_utilization': cpu_utilization,
                        'database_connections': int(database_connections)
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting RDS attributes for {resource_arn}: {e}")
            return {
                'resource_arn': resource_arn,
                'resource_type': 'rds',
                'error': str(e),
                'attributes': {}
            }
    
    def get_apigateway_attributes(self, resource_arn: str) -> Dict[str, Any]:
        """
        Get API Gateway attributes and metrics
        
        Args:
            resource_arn: API Gateway ARN
            
        Returns:
            Dictionary containing API Gateway attributes and metrics
        """
        try:
            # Extract API ID from ARN
            # ARN format: arn:aws:apigateway:region::/restapis/api-id
            api_id = resource_arn.split('/')[-1]
            
            # Get API details
            response = self.apigateway_client.get_rest_api(restApiId=api_id)
            
            return {
                'resource_arn': resource_arn,
                'resource_type': 'apigateway',
                'attributes': {
                    'api_id': response.get('id', ''),
                    'api_name': response.get('name', ''),
                    'description': response.get('description', ''),
                    'created_date': str(response.get('createdDate', '')),
                    'api_key_source': response.get('apiKeySource', ''),
                    'endpoint_configuration': response.get('endpointConfiguration', {}),
                    'metrics': {}  # API Gateway metrics would need stage-specific collection
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting API Gateway attributes for {resource_arn}: {e}")
            return {
                'resource_arn': resource_arn,
                'resource_type': 'apigateway',
                'error': str(e),
                'attributes': {}
            }
    
    def get_elb_attributes(self, resource_arn: str) -> Dict[str, Any]:
        """
        Get ELB/ALB attributes and metrics
        
        Args:
            resource_arn: ELB/ALB ARN
            
        Returns:
            Dictionary containing ELB attributes and metrics
        """
        try:
            # Get load balancer details
            response = self.elbv2_client.describe_load_balancers(LoadBalancerArns=[resource_arn])
            lb = response['LoadBalancers'][0]
            
            # Get CloudWatch metrics
            dimensions = [{'Name': 'LoadBalancer', 'Value': lb['LoadBalancerName']}]
            
            request_count = self._get_cloudwatch_metrics(
                'AWS/ApplicationELB', 'RequestCount', dimensions
            )
            
            target_response_time = self._get_cloudwatch_metrics(
                'AWS/ApplicationELB', 'TargetResponseTime', dimensions
            )
            
            return {
                'resource_arn': resource_arn,
                'resource_type': 'elb',
                'attributes': {
                    'load_balancer_name': lb.get('LoadBalancerName', ''),
                    'dns_name': lb.get('DNSName', ''),
                    'scheme': lb.get('Scheme', ''),
                    'vpc_id': lb.get('VpcId', ''),
                    'type': lb.get('Type', ''),
                    'state': lb.get('State', {}).get('Code', ''),
                    'metrics': {
                        'request_count': int(request_count),
                        'target_response_time_ms': target_response_time * 1000 if target_response_time else 0
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting ELB attributes for {resource_arn}: {e}")
            return {
                'resource_arn': resource_arn,
                'resource_type': 'elb',
                'error': str(e),
                'attributes': {}
            }
