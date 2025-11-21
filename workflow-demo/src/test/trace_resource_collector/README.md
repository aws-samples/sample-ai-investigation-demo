# Trace Resource Collector Node Tests

This directory contains tests for the `trace_resource_collector` node, which is responsible for collecting detailed resource attributes and metrics after trace analysis.

## Overview

The `trace_resource_collector` node is positioned in the workflow right after the `trace_details_analyzer` node. It takes the trace analysis results and collects comprehensive information about the resources involved in the trace.

## Node Position in Workflow

```
trace_details_analyzer → trace_resource_collector → logs_collector → ...
```

## Resource Types Collected

The node collects detailed information for the following AWS resource types:

### 1. EC2 Instances
- **Metrics**: CPU utilization, Memory usage, Network I/O, Disk I/O
- **Status**: Instance state, health checks, security groups
- **Configuration**: Instance type, AMI, key pairs, placement

### 2. Lambda Functions  
- **Key Metrics**: Invocation count, Error rate, Duration, Memory utilization
- **Performance**: Throttles, concurrent executions, cold starts
- **Configuration**: Runtime, memory allocation, timeout settings

### 3. S3 Buckets
- **Bucket Policy**: Access permissions and restrictions
- **Access Patterns**: Request metrics, data transfer patterns
- **Metrics**: Request count, Error rates, Storage metrics

### 4. RDS Databases
- **Performance**: Connection count, CPU, Memory usage
- **I/O Metrics**: Read/Write IOPS, Query performance
- **Configuration**: Engine type, instance class, storage

### 5. API Gateway
- **Request Metrics**: Request count, Latency, Error rates
- **Throttling**: Rate limiting and throttling metrics
- **Configuration**: Stages, methods, integrations

## Test Files

### `test.py`
Main test script that can be run with sample data files.

**Usage:**
```bash
python test.py <test_file.json>
python test.py api_gateway_trace.json
python test.py lambda_trace.json
```

### Sample Test Data

#### `api_gateway_trace.json`
Tests API Gateway scenario with:
- High error rates (15%)
- Backend Lambda timeouts
- Multiple resource dependencies (API Gateway → Lambda → RDS, S3)

#### `lambda_trace.json`
Tests Lambda function scenario with:
- Memory exceeded errors
- Function duration approaching timeout (29.8s)
- High memory usage (512MB)
- Database and S3 dependencies

## Expected Output Structure

The node returns a JSON response with the following structure:

```json
{
  "resource_collection": {
    "ec2_resources": [
      {
        "instance_id": "i-1234567890abcdef0",
        "instance_type": "t3.large",
        "state": "running",
        "cpu_utilization": 75.5,
        "memory_usage": 60.2,
        "network_in": 1024000,
        "network_out": 2048000
      }
    ],
    "lambda_resources": [
      {
        "function_name": "ProcessOrderFunction",
        "runtime": "python3.9",
        "memory_size": 512,
        "timeout": 30,
        "invocations": 1500,
        "errors": 120,
        "duration_avg": 2500,
        "throttles": 5
      }
    ],
    "s3_resources": [
      {
        "bucket_name": "order-processing-bucket",
        "region": "us-east-1",
        "requests": 5000,
        "errors": 25,
        "bucket_policy": {...}
      }
    ],
    "rds_resources": [
      {
        "db_instance_id": "order-database",
        "engine": "mysql",
        "instance_class": "db.t3.micro",
        "cpu_utilization": 45.2,
        "connections": 15,
        "read_iops": 100,
        "write_iops": 50
      }
    ],
    "apigateway_resources": [
      {
        "api_id": "<YOUR-API-ID>", // nosec
        "api_name": "OrderProcessingAPI",
        "stage": "prod",
        "requests": 10000,
        "errors": 1500,
        "latency_avg": 2500,
        "throttles": 10
      }
    ]
  },
  "raw_analysis": "Detailed analysis summary of resource collection findings",
  "recommendations": [
    "Increase Lambda memory allocation to reduce execution time",
    "Review API Gateway throttling limits",
    "Optimize database queries to reduce RDS CPU usage"
  ]
}
```

## Integration with Workflow

The node integrates seamlessly with the existing workflow:

1. **Input**: Receives trace analysis results from `trace_details_analyzer`
2. **Processing**: Collects detailed resource metrics and attributes
3. **Output**: Provides comprehensive resource information to `logs_collector`
4. **Context**: Updates workflow context with `resource_collection` data

## Error Handling

The node includes robust error handling:
- Graceful handling of missing or invalid input data
- Structured JSON error responses
- Detailed logging for debugging
- Fallback to empty resource collections on errors

## Testing

Run the tests to verify functionality:

```bash
# Test API Gateway scenario
cd /path/to/src
python test/trace_resource_collector/test.py test/trace_resource_collector/samples/api_gateway_trace.json

# Test Lambda scenario  
python test/trace_resource_collector/test.py test/trace_resource_collector/samples/lambda_trace.json
```

Both tests should complete successfully with detailed resource collection results.
