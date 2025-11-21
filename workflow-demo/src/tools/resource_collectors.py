"""
Additional resource collectors for AWS services
This file contains methods for collecting attributes from DynamoDB, S3, RDS, API Gateway, and ELB
"""

from typing import Dict, List, Any
import logging
from botocore.exceptions import ClientError

class AdditionalResourceCollectors:
    """Mixin class containing additional resource collection methods"""
    
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
            
            system_errors = self._get_cloudwatch_metrics(
                'AWS/DynamoDB', 'SystemErrors', dimensions
            )
            
            user_errors = self._get_cloudwatch_metrics(
                'AWS/DynamoDB', 'UserErrors', dimensions
            )
            
            return {
                'resource_arn': resource_arn,
                'resource_type': 'dynamodb',
                'attributes': {
                    'table_name': table.get('TableName', ''),
                    'table_status': table.get('TableStatus', 'unknown'),
                    'creation_date': table.get('CreationDateTime', '').isoformat() if table.get('CreationDateTime') else '',
                    'item_count': table.get('ItemCount', 0),
                    'table_size_bytes': table.get('TableSizeBytes', 0),
                    'billing_mode': table.get('BillingModeSummary', {}).get('BillingMode', 'unknown'),
                    'provisioned_throughput': {
                        'read_capacity': table.get('ProvisionedThroughput', {}).get('ReadCapacityUnits', 0),
                        'write_capacity': table.get('ProvisionedThroughput', {}).get('WriteCapacityUnits', 0)
                    },
                    'global_secondary_indexes': len(table.get('GlobalSecondaryIndexes', [])),
                    'local_secondary_indexes': len(table.get('LocalSecondaryIndexes', [])),
                    'metrics': {
                        'consumed_read_capacity': round(consumed_read_capacity, 2),
                        'consumed_write_capacity': round(consumed_write_capacity, 2),
                        'throttled_requests': int(throttled_requests),
                        'system_errors': int(system_errors),
                        'user_errors': int(user_errors)
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
            location_response = self.s3_client.get_bucket_location(Bucket=bucket_name)
            region = location_response.get('LocationConstraint') or 'us-east-1'
            
            # Get bucket policy (if exists)
            bucket_policy = None
            bucket_policy_json = None
            try:
                policy_response = self.s3_client.get_bucket_policy(Bucket=bucket_name)
                bucket_policy = policy_response.get('Policy', '')
                if bucket_policy:
                    # Parse the policy JSON for logging and analysis
                    import json
                    try:
                        bucket_policy_json = json.loads(bucket_policy)
                        self.logger.info(f"S3 bucket {bucket_name} policy: {json.dumps(bucket_policy_json, indent=2)}")
                    except json.JSONDecodeError:
                        self.logger.warning(f"S3 bucket {bucket_name} has invalid JSON policy: {bucket_policy}")
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchBucketPolicy':
                    raise
            
            # Get bucket versioning
            versioning_response = self.s3_client.get_bucket_versioning(Bucket=bucket_name)
            versioning_status = versioning_response.get('Status', 'Disabled')
            
            # Get CloudWatch metrics
            dimensions = [{'Name': 'BucketName', 'Value': bucket_name}]
            
            number_of_objects = self._get_cloudwatch_metrics(
                'AWS/S3', 'NumberOfObjects', dimensions + [{'Name': 'StorageType', 'Value': 'AllStorageTypes'}]
            )
            
            bucket_size_bytes = self._get_cloudwatch_metrics(
                'AWS/S3', 'BucketSizeBytes', dimensions + [{'Name': 'StorageType', 'Value': 'StandardStorage'}]
            )
            
            # Request metrics (if enabled)
            all_requests = self._get_cloudwatch_metrics(
                'AWS/S3', 'AllRequests', dimensions
            )
            
            get_requests = self._get_cloudwatch_metrics(
                'AWS/S3', 'GetRequests', dimensions
            )
            
            put_requests = self._get_cloudwatch_metrics(
                'AWS/S3', 'PutRequests', dimensions
            )
            
            errors_4xx = self._get_cloudwatch_metrics(
                'AWS/S3', '4xxErrors', dimensions
            )
            
            errors_5xx = self._get_cloudwatch_metrics(
                'AWS/S3', '5xxErrors', dimensions
            )
            
            return {
                'resource_arn': resource_arn,
                'resource_type': 's3',
                'attributes': {
                    'bucket_name': bucket_name,
                    'region': region,
                    'versioning_status': versioning_status,
                    'has_bucket_policy': bucket_policy is not None,
                    'bucket_policy_length': len(bucket_policy) if bucket_policy else 0,
                    'bucket_policy': bucket_policy_json if bucket_policy_json else None,
                    'bucket_policy_raw': bucket_policy if bucket_policy else None,
                    'metrics': {
                        'number_of_objects': int(number_of_objects),
                        'bucket_size_bytes': int(bucket_size_bytes),
                        'all_requests': int(all_requests),
                        'get_requests': int(get_requests),
                        'put_requests': int(put_requests),
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
            db_instance_id = resource_arn.split(':')[-1]
            
            # Get DB instance details
            response = self.rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_id)
            
            if not response['DBInstances']:
                return {
                    'resource_arn': resource_arn,
                    'error': f'DB instance {db_instance_id} not found',
                    'attributes': {}
                }
            
            db_instance = response['DBInstances'][0]
            
            # Get CloudWatch metrics
            dimensions = [{'Name': 'DBInstanceIdentifier', 'Value': db_instance_id}]
            
            cpu_utilization = self._get_cloudwatch_metrics(
                'AWS/RDS', 'CPUUtilization', dimensions
            )
            
            database_connections = self._get_cloudwatch_metrics(
                'AWS/RDS', 'DatabaseConnections', dimensions
            )
            
            read_iops = self._get_cloudwatch_metrics(
                'AWS/RDS', 'ReadIOPS', dimensions
            )
            
            write_iops = self._get_cloudwatch_metrics(
                'AWS/RDS', 'WriteIOPS', dimensions
            )
            
            read_latency = self._get_cloudwatch_metrics(
                'AWS/RDS', 'ReadLatency', dimensions
            )
            
            write_latency = self._get_cloudwatch_metrics(
                'AWS/RDS', 'WriteLatency', dimensions
            )
            
            freeable_memory = self._get_cloudwatch_metrics(
                'AWS/RDS', 'FreeableMemory', dimensions
            )
            
            return {
                'resource_arn': resource_arn,
                'resource_type': 'rds',
                'attributes': {
                    'db_instance_id': db_instance.get('DBInstanceIdentifier', ''),
                    'db_instance_class': db_instance.get('DBInstanceClass', ''),
                    'engine': db_instance.get('Engine', ''),
                    'engine_version': db_instance.get('EngineVersion', ''),
                    'db_instance_status': db_instance.get('DBInstanceStatus', 'unknown'),
                    'allocated_storage': db_instance.get('AllocatedStorage', 0),
                    'storage_type': db_instance.get('StorageType', ''),
                    'multi_az': db_instance.get('MultiAZ', False),
                    'availability_zone': db_instance.get('AvailabilityZone', ''),
                    'vpc_id': db_instance.get('DBSubnetGroup', {}).get('VpcId', ''),
                    'publicly_accessible': db_instance.get('PubliclyAccessible', False),
                    'backup_retention_period': db_instance.get('BackupRetentionPeriod', 0),
                    'metrics': {
                        'cpu_utilization': round(cpu_utilization, 2),
                        'database_connections': int(database_connections),
                        'read_iops': round(read_iops, 2),
                        'write_iops': round(write_iops, 2),
                        'read_latency_ms': round(read_latency * 1000, 2),
                        'write_latency_ms': round(write_latency * 1000, 2),
                        'freeable_memory_bytes': int(freeable_memory)
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
            api_id = resource_arn.split('/')[-1]
            
            # Get REST API details
            response = self.apigateway_client.get_rest_api(restApiId=api_id)
            
            # Get stages
            stages_response = self.apigateway_client.get_stages(restApiId=api_id)
            stages = stages_response.get('item', [])
            
            # Get CloudWatch metrics for each stage
            stage_metrics = {}
            for stage in stages:
                stage_name = stage.get('stageName', '')
                dimensions = [
                    {'Name': 'ApiName', 'Value': response.get('name', '')},
                    {'Name': 'Stage', 'Value': stage_name}
                ]
                
                count = self._get_cloudwatch_metrics(
                    'AWS/ApiGateway', 'Count', dimensions
                )
                
                latency = self._get_cloudwatch_metrics(
                    'AWS/ApiGateway', 'Latency', dimensions
                )
                
                errors_4xx = self._get_cloudwatch_metrics(
                    'AWS/ApiGateway', '4XXError', dimensions
                )
                
                errors_5xx = self._get_cloudwatch_metrics(
                    'AWS/ApiGateway', '5XXError', dimensions
                )
                
                stage_metrics[stage_name] = {
                    'requests': int(count),
                    'latency_ms': round(latency, 2),
                    'errors_4xx': int(errors_4xx),
                    'errors_5xx': int(errors_5xx)
                }
            
            return {
                'resource_arn': resource_arn,
                'resource_type': 'apigateway',
                'attributes': {
                    'api_id': response.get('id', ''),
                    'api_name': response.get('name', ''),
                    'description': response.get('description', ''),
                    'created_date': response.get('createdDate', '').isoformat() if response.get('createdDate') else '',
                    'api_key_source': response.get('apiKeySource', ''),
                    'endpoint_configuration': response.get('endpointConfiguration', {}),
                    'stages': [stage.get('stageName', '') for stage in stages],
                    'stage_metrics': stage_metrics
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
        Get ELB (Application/Network Load Balancer) attributes and metrics
        
        Args:
            resource_arn: ELB ARN
            
        Returns:
            Dictionary containing ELB attributes and metrics
        """
        try:
            # Get load balancer details
            response = self.elbv2_client.describe_load_balancers(LoadBalancerArns=[resource_arn])
            
            if not response['LoadBalancers']:
                return {
                    'resource_arn': resource_arn,
                    'error': 'Load balancer not found',
                    'attributes': {}
                }
            
            lb = response['LoadBalancers'][0]
            lb_name = lb.get('LoadBalancerName', '')
            
            # Get target groups
            tg_response = self.elbv2_client.describe_target_groups(LoadBalancerArn=resource_arn)
            target_groups = tg_response.get('TargetGroups', [])
            
            # Get CloudWatch metrics
            dimensions = [{'Name': 'LoadBalancer', 'Value': f"{lb.get('Type', '')}/{lb_name}/{lb.get('LoadBalancerArn', '').split('/')[-1]}"}]
            
            request_count = self._get_cloudwatch_metrics(
                'AWS/ApplicationELB', 'RequestCount', dimensions
            )
            
            target_response_time = self._get_cloudwatch_metrics(
                'AWS/ApplicationELB', 'TargetResponseTime', dimensions
            )
            
            http_4xx_count = self._get_cloudwatch_metrics(
                'AWS/ApplicationELB', 'HTTPCode_Target_4XX_Count', dimensions
            )
            
            http_5xx_count = self._get_cloudwatch_metrics(
                'AWS/ApplicationELB', 'HTTPCode_Target_5XX_Count', dimensions
            )
            
            healthy_host_count = self._get_cloudwatch_metrics(
                'AWS/ApplicationELB', 'HealthyHostCount', dimensions
            )
            
            unhealthy_host_count = self._get_cloudwatch_metrics(
                'AWS/ApplicationELB', 'UnHealthyHostCount', dimensions
            )
            
            return {
                'resource_arn': resource_arn,
                'resource_type': 'elasticloadbalancing',
                'attributes': {
                    'load_balancer_name': lb_name,
                    'load_balancer_type': lb.get('Type', ''),
                    'scheme': lb.get('Scheme', ''),
                    'state': lb.get('State', {}).get('Code', 'unknown'),
                    'vpc_id': lb.get('VpcId', ''),
                    'availability_zones': [az.get('ZoneName', '') for az in lb.get('AvailabilityZones', [])],
                    'security_groups': lb.get('SecurityGroups', []),
                    'ip_address_type': lb.get('IpAddressType', ''),
                    'target_groups_count': len(target_groups),
                    'created_time': lb.get('CreatedTime', '').isoformat() if lb.get('CreatedTime') else '',
                    'metrics': {
                        'request_count': int(request_count),
                        'target_response_time_ms': round(target_response_time * 1000, 2),
                        'http_4xx_count': int(http_4xx_count),
                        'http_5xx_count': int(http_5xx_count),
                        'healthy_host_count': int(healthy_host_count),
                        'unhealthy_host_count': int(unhealthy_host_count)
                    }
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting ELB attributes for {resource_arn}: {e}")
            return {
                'resource_arn': resource_arn,
                'resource_type': 'elasticloadbalancing',
                'error': str(e),
                'attributes': {}
            }
