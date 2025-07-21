# AWS Resource Attributes Collector Tools

This directory contains tools for collecting detailed attributes and metrics from various AWS resources. These tools are used by the AIOps workflow to gather real-time resource information for troubleshooting and root cause analysis.

## Overview

The Resource Attributes Collector provides comprehensive methods to collect detailed attributes and metrics for various AWS resources including:

- **EC2 Instances**: Status, CPU usage, network metrics, disk I/O
- **Lambda Functions**: Success rate, throttles, duration, memory usage
- **DynamoDB Tables**: Throttle metrics, capacity utilization, error rates
- **S3 Buckets**: Request metrics, error rates, bucket policies
- **RDS Instances**: CPU usage, connections, I/O metrics, latency
- **API Gateway**: Request count, latency, error rates, throttling
- **Load Balancers**: Health checks, request metrics, target status

## Files

### `resource_attributes_collector.py`
Main collector class that provides methods for collecting attributes from AWS resources.

### `resource_collectors.py`
Additional collector methods for DynamoDB, S3, RDS, API Gateway, and ELB resources.

### `resource_utils.py`
Utility functions for:
- Collecting multiple resource attributes
- Extracting ARNs from text
- Formatting results for display
- Generating resource summaries

### `test_resource_collector.py`
Test script for validating the resource collector functionality.

## Usage

### Basic Usage

```python
from tools.resource_attributes_collector import ResourceAttributesCollector

# Initialize collector
collector = ResourceAttributesCollector(region_name='us-east-1')

# Collect attributes for a single resource
arn = "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0"
attributes = collector.collect_resource_attributes(arn)

print(f"Resource Type: {attributes['resource_type']}")
print(f"Attributes: {attributes['attributes']}")
```

### Multiple Resources

```python
from tools.resource_utils import collect_multiple_resource_attributes

arns = [
    "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0",
    "arn:aws:lambda:us-east-1:123456789012:function:MyFunction",
    "arn:aws:s3:::my-bucket"
]

results = collect_multiple_resource_attributes(arns)
print(f"EC2 Resources: {len(results['ec2_resources'])}")
print(f"Lambda Resources: {len(results['lambda_resources'])}")
```

### Extract ARNs from Text

```python
from tools.resource_utils import extract_resource_arns_from_text

text = "The issue affects arn:aws:ec2:us-east-1:123456789012:instance/i-123 and arn:aws:lambda:us-east-1:123456789012:function:MyFunc"
arns = extract_resource_arns_from_text(text)
print(f"Found ARNs: {arns}")
```

## Resource-Specific Attributes

### EC2 Instances
- Instance ID, type, state, availability zone
- CPU utilization, network I/O, disk operations
- Security groups, VPC information
- Instance and system status checks

### Lambda Functions
- Function name, runtime, memory size, timeout
- Invocation count, error count, success rate
- Average duration, throttles, concurrent executions
- Environment variables and layers count

### DynamoDB Tables
- Table name, status, item count, size
- Consumed read/write capacity units
- Throttled requests, system/user errors
- Billing mode and provisioned throughput

### S3 Buckets
- Bucket name, region, versioning status
- Number of objects, bucket size
- Request metrics (GET, PUT, errors)
- Bucket policy presence and size

### RDS Instances
- Instance ID, class, engine, version
- CPU utilization, database connections
- Read/write IOPS and latency
- Storage information and backup settings

### API Gateway
- API ID, name, description, stages
- Request count, latency, error rates per stage
- Endpoint configuration and creation date

### Load Balancers
- Load balancer name, type, scheme, state
- Request count, response time, error rates
- Healthy/unhealthy host counts
- Target groups and availability zones

## Testing

Run the test script to verify functionality:

```bash
# Test with sample ARNs (may show errors if resources don't exist)
python tools/test_resource_collector.py

# Test with specific ARNs
python tools/test_resource_collector.py arn:aws:ec2:... arn:aws:lambda:...
```

## Integration with AIOps Workflow

The tools are integrated with the `trace_resource_collector` agent and node:

1. **ARN Extraction**: Automatically extracts resource ARNs from trace analysis results
2. **Attribute Collection**: Collects real-time metrics and attributes for each resource
3. **Recommendation Generation**: Provides actionable recommendations based on collected data
4. **Error Handling**: Gracefully handles AWS API errors and missing resources

## Requirements

- AWS credentials configured (via AWS CLI, environment variables, or IAM roles)
- Appropriate IAM permissions for the AWS services being queried
- boto3 library installed

## Error Handling

The tools include comprehensive error handling:
- AWS credential errors
- Resource not found errors
- CloudWatch metric unavailability
- Network connectivity issues
- Malformed ARNs

All errors are logged and returned in structured format for downstream processing.

## Performance Considerations

- CloudWatch metrics are queried for the last 10 minutes by default
- Metrics are cached for 5-minute periods to reduce API calls
- Batch operations are used where possible to minimize API requests
- Timeouts are configured to prevent hanging operations

## Security

- Uses least-privilege IAM permissions
- No sensitive data is logged or stored
- AWS credentials are handled securely through boto3
- Resource ARNs are validated before processing
