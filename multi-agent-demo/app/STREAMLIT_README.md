# AIOps Streamlit Monitor

Real-time monitoring and triggering interface for AIOps investigations.

## Features

### 🚀 Trigger Tab

- Multi-line alarm input
- Direct invocation of AgentCore Runtime
- Real-time response display

### 📊 Investigations Tab

- List all investigations
- View workflow status and execution plan
- View investigation context (findings, timeline, confidence)
- Auto-refresh every 5 seconds (optional)

### 🔄 Progress Monitor Tab

- Real-time investigation progress tracking
- View investigation steps with status (completed/pending)
- Display task outputs and findings
- Timeline of events
- Investigation-specific logs with color-coded levels

### 📝 Logs Tab

- Fetch CloudWatch logs from AgentCore Runtime
- Time range selection (1-60 minutes)
- Filter pattern support
- Real-time log display

## Setup

### 1. Install Dependencies

```bash
pip install -r streamlit_requirements.txt
```

### 2. Configure Environment

Edit `run_streamlit.sh` with your values:

```bash
export AGENT_RUNTIME_ARN="arn:aws:bedrock-agentcore:REGION:ACCOUNT:runtime/RUNTIME_NAME"
export INVESTIGATIONS_TABLE="aiops-investigations"
export CONTEXT_TABLE="aiops-investigation-context"
export LOGS_TABLE="aiops-logs"
export AGENTCORE_LOG_GROUP="/aws/bedrock-agentcore/runtime"
export AWS_REGION="ap-southeast-1"
```

#### Get Configuration Values from CDK

Agent Runtime ARN:

```bash
# From CDK output
aws cloudformation describe-stacks \
  --stack-name aiops-demo-main \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentRuntimeArn`].OutputValue' \
  --output text

# Or list runtimes
aws bedrock-agentcore list-runtimes --region ap-southeast-1
```

DynamoDB Table Names:

```bash
# Get all table names from CDK stack
aws cloudformation describe-stacks \
  --stack-name aiops-demo-main \
  --query 'Stacks[0].Outputs[?contains(OutputKey, `Table`)].{Key:OutputKey,Value:OutputValue}' \
  --output table

# Or list tables directly
aws dynamodb list-tables --region ap-southeast-1 | grep aiops
```

The default table names are:

- `INVESTIGATIONS_TABLE`: `aiops-investigations` (workflow and tasks)
- `CONTEXT_TABLE`: `aiops-investigation-context` (status, findings, timeline)
- `LOGS_TABLE`: `aiops-logs` (investigation logs)

Note: Use the runtime ARN (not the endpoint ARN). Format: `arn:aws:bedrock-agentcore:REGION:ACCOUNT:runtime/RUNTIME_NAME`

### 3. Run

```bash
./run_streamlit.sh
```

Or manually:

```bash
export AGENT_RUNTIME_ARN="..."
export AWS_REGION="ap-southeast-1"
streamlit run streamlit_app.py
```

## Usage

### Trigger Investigation

1. Go to **🚀 Trigger** tab
2. Paste alarm content (JSON or text)
3. Click **🚀 Trigger**
4. View investigation ID and response

Example alarm input:

```json
{
  "AlarmName": "HighCPU",
  "MetricName": "CPUUtilization",
  "Namespace": "AWS/EC2",
  "Threshold": 80,
  "Dimensions": [{"Name": "InstanceId", "Value": "i-1234567890"}]
}
```

### Monitor Investigations

1. Go to **📊 Investigations** tab
2. Enable **Auto-refresh** in sidebar for real-time updates
3. Expand investigation to view:
   - Workflow status and execution plan
   - Context with findings and timeline
   - Confidence score and hypothesis

### Track Progress in Real-Time

1. Go to **🔄 Progress Monitor** tab
2. Enter investigation ID (from trigger response or investigations list)
3. Click **🔄 Refresh Monitor** to update
4. View:
   - Status, confidence, and task completion metrics
   - Investigation steps with outputs (✅ completed, ⏳ pending)
   - Findings from specialized agents
   - Timeline of events
   - Investigation logs with color-coded levels (🔴 ERROR, 🟡 WARNING, 🔵 INFO)

### View Logs

1. Go to **📝 Logs** tab
2. Set time range (minutes back)
3. Optional: Add filter pattern (e.g., "ERROR", "investigation_id")
4. Click **📝 Fetch Logs**

## IAM Permissions

Ensure your AWS credentials have:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:InvokeAgentRuntime",
        "dynamodb:Scan",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "logs:FilterLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

## Troubleshooting

Error: Agent Runtime ARN not configured

- Set `AGENT_RUNTIME_ARN` environment variable
- Or enter it in the sidebar

Error: No investigations found

- Trigger an investigation first
- Check DynamoDB table names are correct
- Verify AWS credentials have DynamoDB permissions

Error: No logs found

- Verify log group name
- Check time range
- Ensure AgentCore Runtime has executed

Progress Monitor shows no data

- Verify investigation ID is correct
- Check all three table names are configured
- Ensure tables exist in DynamoDB

## Tips

- Use auto-refresh to monitor active investigations
- Use Progress Monitor tab to track specific investigation in detail
- Filter logs by investigation_id to track specific investigations
- Check context confidence to assess investigation progress
- Monitor timeline to see investigation flow
