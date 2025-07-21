# Decision Node Custom Tests

This directory contains custom test scripts specifically for testing the decision_node with different alarm scenarios.

## Available Tests

- **test.py**: Tests the real decision_node implementation with actual agent calls to AWS Bedrock models

## Sample Files

The `samples` directory contains sample alarm analysis JSON files:

- **api_gateway_alarm.json**: API Gateway error rate alarm analysis
- **rds_connection_alarm.json**: RDS database connection failures alarm analysis
- **cpu_utilization_alarm.json**: EC2 high CPU utilization alarm analysis

## Running Tests

### Testing with All Sample Files

```bash
cd /Users/yagrxu/me/collaborations/2025/aiops/ai-investigation-demo/src
python local/decision/test.py --all
```

### Testing with a Specific Sample File

```bash
cd /Users/yagrxu/me/collaborations/2025/aiops/ai-investigation-demo/src
python local/decision/test.py --file local/decision/samples/api_gateway_alarm.json
```

### Testing with a Custom Message

```bash
cd /Users/yagrxu/me/collaborations/2025/aiops/ai-investigation-demo/src
python local/decision/test.py --file local/decision/samples/rds_connection_alarm.json --message "Please analyze this RDS connection alarm"
```

## Test Output

The test script will:

1. Load the alarm analysis from the specified file
2. Pass it to the real decision_node implementation
3. Display the agent's response
4. Show the initial_decision object in the context
5. Print key information extracted from the decision

## Decision Node Output Format

The decision_node outputs a decision in the context with the following structure:

```json
{
  "alert_type": "error",
  "resource_type": "API Gateway",
  "severity": "High",
  "recommended_path": "trace",
  "reasoning": "Detailed explanation of the decision"
}
```

### Fields

- **alert_type**: Type of alert (performance, availability, error)
- **resource_type**: Type of resource involved (EC2, Lambda, RDS, etc.)
- **severity**: Severity level (Critical, High, Medium, Low)
- **recommended_path**: Investigation path (trace or resource)
- **reasoning**: Detailed explanation of the decision

## Creating New Sample Files

To create a new sample file:

1. Create a JSON file in the samples directory
2. Follow the structure of the existing sample files
3. Include all necessary fields for the alarm analysis

Example:

```json
{
  "identified_alarm_types": ["Custom Alarm Type"],
  "severity": "Critical",
  "extracted_info": {
    "alarm_name": "Custom-Alarm",
    "related_resources": [
      {
        "resource_id": "custom-resource-id",
        "resource_type": "AWS::Custom::Resource"
      }
    ]
  }
}
```
