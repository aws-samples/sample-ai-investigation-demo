# AIOps Architecture Design

## Overview

Task-driven multi-agent system with MCP gateway integration for AWS CloudWatch alarm root cause analysis. Features adaptive workflow generation with context tracking and feedback loops.

## Flow

```
CloudWatch Alarm 
    ↓
Brain Agent (analyzes alarm, generates tasks, initializes context)
    ↓ (SQS: EXECUTION)
Executor Agent (executes task, updates context)
    ↓ (SQS: RE_EVALUATE)
Brain Agent (re-evaluates based on findings, adapts workflow)
    ↓ (SQS: EXECUTION if needed)
Executor Agent (continues execution)
    ↓
Specialized Agents (use MCP tools from gateways)
    ↓
MCP Gateways (expose domain-specific tools)
    ↓
AWS Services (CloudWatch, EC2, RDS, etc.)
```

## Message Flow

```
1. ALARM → Brain Agent
   - Process alarm text
   - Generate workflow
   - Initialize context in DynamoDB
   - Send SQS (EXECUTION)

2. EXECUTION → Executor Agent
   - Get next task
   - Execute with specialized agent
   - Update context with findings (task_id prefix)
   - Add timeline event
   - Send SQS (RE_EVALUATE)

3. RE_EVALUATE → Brain Agent
   - Read accumulated context
   - Assess confidence and findings
   - Decide: continue, add tasks, or conclude
   - Send SQS (EXECUTION) if needed
```

## Components

### 1. Brain Agent
- Processes CloudWatch alarms
- Generates investigation tasks with specific prompts
- Initializes investigation context
- Re-evaluates workflow based on findings
- Assesses confidence levels
- Creates analysis reports

### 2. Executor Agent
- Receives tasks from Brain Agent
- Creates new agent instance per task (with task-specific prompt)
- Updates investigation context after each task
- Logs timeline events
- Triggers Brain Agent re-evaluation via SQS

### 3. Specialized Agents

| Agent | Purpose | Gateways |
|-------|---------|----------|
| LogsAgent | CloudWatch Logs analysis | observability-gateway |
| TraceGraphAgent | X-Ray service graph analysis | observability-gateway |
| ChangeDetectionAgent | CloudTrail change detection + AWS CLI | aws-ops-gateway |
| NotificationAgent | Alert delivery | notification-gateway |

### 4. MCP Gateways

**Observability Gateway**
- CloudWatch Logs query tools
- X-Ray service graph query tools

**AWS Ops Gateway**
- CloudTrail events query (Lambda function)
- AWS CLI tools (Python functions: get_resource_info, get_resource_config)

**Notification Gateway**
- Feishu notification tool

### 5. Data Stores

**Investigation Workflow Table** (`aiops-investigations`)
- Partition Key: `investigation_id`
- Sort Key: `item_type` (METADATA | TASK#{task_id} | RESULT#{task_id})
- Stores: workflow metadata, tasks, execution plan, results

**Investigation Context Table** (`aiops-investigation-context`)
- Partition Key: `investigation_id`
- Single row per investigation
- Stores: alarm_summary, status, confidence, hypothesis, findings, timeline
- Findings keyed by: `{task_id}_{agent_type}` to avoid duplication

## Design Decisions

### 1. Tool Access: Pre-configured (Static Mapping)
**Why**: Simplicity over dynamic discovery
- Agent-to-gateway mapping defined in `gateway_config.py`
- No runtime discovery complexity
- Clear, predictable tool access

### 2. Authentication: IAM (SigV4)
**Why**: Simpler than Cognito JWT
- Uses existing AWS credentials
- No token management needed
- Tested and working

### 3. Agent-Gateway Mapping: 1:N
**Why**: Flexibility with typical simplicity
- Most agents use 1 gateway
- Some agents can use multiple gateways if needed
- Example: HybridAgent uses both observability + resources

### 4. Agent Lifecycle: One Agent Per Task
**Why**: Task-specific prompts
- Each task has unique prompt requirements
- Fresh agent instance per task
- No state pollution between tasks

### 5. Context Storage: Single Row Per Investigation
**Why**: Simplicity and atomic updates
- One DynamoDB item per investigation
- Task-prefixed findings prevent duplication
- Easy to query full context
- Supports incremental updates

### 6. Feedback Loop: Executor → Brain Re-evaluation
**Why**: Adaptive workflow generation
- Brain can adjust based on findings
- Add tasks if confidence is low
- Conclude if confidence is high
- Dynamic investigation strategy

### 7. Message Queue: Single SQS Queue
**Why**: Simplicity
- One queue for all message types (ALARM, EXECUTION, RE_EVALUATE)
- Message type routing in main.py
- Simpler infrastructure

## Tool Loading Flow

```python
# 1. Agent requests tools
tools = load_tools_for_agent("LogsAgent")

# 2. Tool loader checks config
gateways = get_gateways_for_agent("LogsAgent")  # ["observability-gateway"]

# 3. For each gateway
gateway_url = get_gateway_url("observability-gateway")  # from env

# 4. Create MCP client with SigV4
mcp_client = create_gateway_mcp_client(gateway_url)

# 5. List tools from gateway
tools = mcp_client.list_tools_sync()

# 6. Return tools to agent
return tools
```

## Context Update Flow

```python
# 1. Executor completes task
result = execute_task(task, investigation_id)

# 2. Update context with findings
context_store.update_finding(
    investigation_id,
    task_id="task-1",
    agent_type="LogsAgent",
    finding_data={"errors_found": 15, "result": "..."}
)
# Stored as: findings["task-1_LogsAgent"]

# 3. Add timeline event
context_store.add_timeline_event(
    investigation_id,
    "Task task-1 completed by LogsAgent",
    "LogsAgent"
)

# 4. Brain reads context for re-evaluation
context = context_store.get_context(investigation_id)
# Contains: alarm_summary, findings, timeline, confidence, etc.
```

## Environment Configuration

Required environment variables (from CDK outputs):

```bash
OBSERVABILITY_GATEWAY_URL="https://xxx.gateway.bedrock-agentcore.REGION.amazonaws.com/mcp"
AWS_OPS_GATEWAY_URL="https://xxx.gateway.bedrock-agentcore.REGION.amazonaws.com/mcp"
NOTIFICATION_GATEWAY_URL="https://xxx.gateway.bedrock-agentcore.REGION.amazonaws.com/mcp"
INVESTIGATION_QUEUE_URL="https://sqs.REGION.amazonaws.com/ACCOUNT/aiops-investigations"
INVESTIGATIONS_TABLE="aiops-investigations"
CONTEXT_TABLE="aiops-investigation-context"
AWS_REGION="ap-southeast-1"
```

## Implementation Status

✅ **Completed:**
- Architecture design
- Gateway configuration structure
- MCP client with SigV4 auth
- Tool loader implementation
- Brain Agent with workflow generation
- Executor Agent with task execution
- Context store with single-row design
- Feedback loop (Executor → Brain)
- SQS message routing
- DynamoDB tables and permissions
- Three MCP gateways (Observability, AWS Ops, Notification)
- AWS CLI tools (get_resource_info, get_resource_config)
- Specialized agents: LogsAgent, TraceGraphAgent, ChangeDetectionAgent, NotificationAgent

🚧 **Next Steps:**
1. Test end-to-end workflow
2. Add MetricsAgent for CloudWatch Metrics analysis
3. Implement confidence-based workflow adaptation
4. Create monitoring and observability
