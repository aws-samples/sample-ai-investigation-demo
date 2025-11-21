"""Brain Agent for alarm analysis and workflow generation."""

from strands import Agent
from strands.models import BedrockModel
from aiops.tools.gateway_config import AGENT_GATEWAY_CONFIG, get_agent_description
from aiops.tools.storage_tools import save_investigation_workflow, trigger_investigation, update_confidence, remove_pending_tasks, add_tasks_to_workflow, update_task_description
from aiops.tools.aws_cli_tools import get_resource_info, get_resource_config
from aiops.utils.context_store import InvestigationContextStore
from aiops.utils.online_logger import log
from aiops.models.enums import MessageType
from typing import Dict
import json
import uuid
import boto3
import os

# Configuration
MAX_TASKS_PER_INVESTIGATION = int(os.getenv('MAX_TASKS_PER_INVESTIGATION', '5'))

class BrainAgent:
    """Brain Agent processes alarms and generates investigation workflows."""
    
    def __init__(self):
        self.model = BedrockModel(model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0")
        self.context_store = InvestigationContextStore()
        self.sqs = boto3.client('sqs')
        self.agent = Agent(
            model=self.model,
            tools=[save_investigation_workflow, trigger_investigation, get_resource_info, get_resource_config],
            system_prompt=self._get_system_prompt()
        )
        self.evaluator_agent = Agent(
            model=self.model,
            tools=[update_confidence, add_tasks_to_workflow, trigger_investigation, remove_pending_tasks, update_task_description],
            system_prompt=self._get_evaluator_prompt()
        )
    
    def _get_system_prompt(self) -> str:
        # Dynamically build available agents list with descriptions
        agents_info = []
        for agent_name in AGENT_GATEWAY_CONFIG.keys():
            description = get_agent_description(agent_name)
            agents_info.append(f"- {agent_name}: {description}")
        
        agents_list = "\n".join(agents_info)
        
        return f"""You are the Brain Agent for AIOps root cause analysis.

Your responsibilities:
1. Extract alarm information from input text
2. Use get_resource_info to find exact resource IDs/ARNs (Lambda functions, API Gateways, DynamoDB tables, EC2 instances, etc.)
3. Use get_resource_config to get detailed resource configurations if needed
4. Understand resources involved from Trace Graph analysis
5. Categorize the alarm type and identify affected resources
6. Generate investigation tasks for specialized agents with accurate resource IDs
7. Save the workflow using save_investigation_workflow tool
8. Trigger execution using trigger_investigation tool

Available tools:
- get_resource_info(service, operation, parameters): Execute AWS CLI to list/describe resources
  Examples:
  - get_resource_info('lambda', 'list_functions', {{}})
  - get_resource_info('lambda', 'get_function', {{'FunctionName': 'my-func'}})
  - get_resource_info('dynamodb', 'describe_table', {{'TableName': 'my-table'}})
  - get_resource_info('ec2', 'describe_instances', {{'InstanceIds': ['i-xxx']}})
- get_resource_config(service, operation, parameters): Get detailed resource configurations

Available specialized agents:
{agents_list}

When processing alarm text:
- Extract: alarm name, metric, namespace, threshold, dimensions, state
- Use AWS CLI tools to get exact resource IDs/ARNs from partial names or dimensions
- Identify affected resources with accurate ARNs or IDs
- Determine alarm severity and impact

IMPORTANT: 
1. Always use get_resource_info to get accurate resource IDs before creating tasks
2. After generating and saving workflow, call trigger_investigation to start execution
3. If you decide to notify the on-call team, put the task after the investigation tasks
4. Include alarm key information in the notification task description

Response format for workflow:
{{
  "alarm_summary": {{
    "resource_name": "string - alarm name",
    "metric": "string - metric name",
    "namespace": "string - AWS namespace",
    "resource_id": "string - affected resource ID",
    "time": "string - converts to an integer (removes milliseconds/decimal places)"
  }},
  "tasks": [
    {{
      "task_id": "string - unique task ID (e.g., task-1)",
      "agent_type": "string - one of the available agents",
      "description": "string - specific investigation task with detail information provided in description",
      "priority": number - priority level (1=highest)
    }}
  ]
}}

Select appropriate agents based on alarm type and generate actionable investigation tasks."""
    
    def _get_evaluator_prompt(self) -> str:
        """Get system prompt for re-evaluation."""
        agents_info = []
        for agent_name in AGENT_GATEWAY_CONFIG.keys():
            description = get_agent_description(agent_name)
            agents_info.append(f"- {agent_name}: {description}")
        
        agents_list = "\n".join(agents_info)
        
        return f"""You are the Brain Agent evaluating investigation progress.

Your responsibilities:
1. Analyze accumulated findings from completed tasks
2. Assess confidence level (0.0-1.0) based on evidence
3. Optionally update pending tasks with specific resource names from findings
4. Determine if investigation should continue or conclude

Available specialized agents:
{agents_list}

CRITICAL: Evaluation workflow:
1. FIRST: Call update_confidence with your assessment
2. SECOND: If findings contain specific resource ARNs/IDs, update pending tasks
   - Use update_task_description to update a task with specific resource names (simpler)
   - OR use remove_pending_tasks + add_tasks_to_workflow to replace tasks entirely
3. FINAL: ALWAYS call trigger_investigation if pending tasks exist
   - Check if confidence >= 0.7 and no pending tasks: provide summary only
   - Otherwise: MUST call trigger_investigation to continue execution
   - If confidence < 0.7: refer to task management section below, optionally add/remove tasks, then call trigger_investigation

Confidence criteria:
- 0.9-1.0: Definitive root cause identified with strong evidence AND triggering change identified from CloudTrail/audit logs
- 0.7-0.9: Clear root cause with supporting evidence, but triggering change not yet confirmed
- 0.5-0.7: Hypothesis formed but needs validation or change detection
- 0.0-0.5: Insufficient evidence, continue investigation

task management:
- Only update tasks if findings reveal specific resources that would improve investigation
- Remove unhelpful or redundant tasks
- Add new tasks only if current tasks are insufficient
- Tasks are automatically resequenced by priority after changes

Final step:
- Call trigger_investigation if pending tasks exist
- Provide summary if investigation is complete"""
    
    def process_alarm_text(self, alarm_text: str, investigation_id: str = None) -> str:
        """Process alarm text and generate investigation workflow.
        
        Args:
            alarm_text: Raw alarm text (JSON or plain text)
            investigation_id: Investigation ID (generates UUID if not provided)
            
        Returns:
            Investigation ID
        """
        if investigation_id is None:
            investigation_id = str(uuid.uuid4())
        
        log("brain-init", f"Processing alarm for investigation {investigation_id}", investigation_id=investigation_id)
        
        prompt = f"""Analyze this CloudWatch alarm and generate investigation workflow.

Investigation ID: {investigation_id}
Alarm:
{alarm_text}

Generate tasks and save the workflow using save_investigation_workflow tool."""
        
        response = self.agent(prompt)
        
        # Initialize context (alarm_summary will be extracted from workflow)
        try:
            from aiops.utils.dynamodb_helper import InvestigationStore
            from datetime import datetime
            store = InvestigationStore()
            workflow = store.get_workflow(investigation_id)
            alarm_summary = workflow.get('alarm_summary', {})

            if alarm_summary:
                # Check if time is too old (LLM using training cutoff date)
                current_timestamp = int(datetime.utcnow().timestamp())
                alarm_time = int(alarm_summary.get('time', current_timestamp))
                
                # If alarm time is more than 7 days old, replace with current time
                if abs(current_timestamp - alarm_time) > 604800:  # 7 days in seconds
                    log("brain-init", f"Alarm time {alarm_time} is >7 days old, replacing with current time {current_timestamp}", investigation_id=investigation_id)
                    alarm_summary['time'] = str(current_timestamp)
                    
                    # Update the entire alarm_summary in DynamoDB
                    metadata = store.table.get_item(
                        Key={'investigation_id': investigation_id, 'item_type': 'METADATA'}
                    )['Item']
                    metadata['alarm_summary'] = alarm_summary
                    store.table.put_item(Item=metadata)
                
                self.context_store.create_context(investigation_id, alarm_summary)
                log("brain-init", f"Context initialized with {len(workflow.get('tasks', []))} tasks", investigation_id=investigation_id)
                print(f"✅ Context initialized for {investigation_id}")
                
                # Trigger execution (in case LLM didn't call trigger_investigation)
                from aiops.utils.sqs_helper import send_execution_message
                send_execution_message(investigation_id, 'init')
                log("brain-init", f"Execution triggered for {investigation_id}", investigation_id=investigation_id)
        except Exception as e:
            log("brain-init", f"Failed to initialize context: {e}", level="ERROR", investigation_id=investigation_id)
            print(f"⚠️  Failed to initialize context: {e}")
        return investigation_id
    
    def re_evaluate_workflow(self, investigation_id: str) -> str:
        """Re-evaluate workflow based on current context and findings.

        Args:
            investigation_id: Investigation ID
            
        Returns:
            Status message
        """
        log("brain-evaluate", f"Re-evaluating investigation {investigation_id}", investigation_id=investigation_id)
        
        # Get current context
        context = self.context_store.get_context(investigation_id)
        if not context:
            log("brain-evaluate", f"No context found for {investigation_id}", level="ERROR", investigation_id=investigation_id)
            return f"Error: No context found for {investigation_id}"
        
        # Get current workflow
        from aiops.utils.dynamodb_helper import InvestigationStore
        store = InvestigationStore()
        workflow = store.get_workflow(investigation_id)
        
        total_tasks = len(workflow.get('tasks', []))
        completed = len([t for t in workflow.get('tasks', []) if t.get('status') == 'COMPLETED'])
        pending = len([t for t in workflow.get('tasks', []) if t.get('status') == 'PENDING'])
        
        log("brain-evaluate", f"Total: {total_tasks}/{MAX_TASKS_PER_INVESTIGATION}, Completed: {completed}, Pending: {pending}, Confidence: {context.get('confidence', 0)}", investigation_id=investigation_id)

        # Force conclusion if max tasks reached
        if total_tasks >= MAX_TASKS_PER_INVESTIGATION:
            log("brain-evaluate", f"Max tasks ({MAX_TASKS_PER_INVESTIGATION}) reached, forcing conclusion", investigation_id=investigation_id)
            self.context_store.update_status(investigation_id, "COMPLETED")
            return f"Investigation concluded: Max tasks limit reached"

        # Get pending tasks details
        pending_tasks = [t for t in workflow.get('tasks', []) if t.get('status') == 'PENDING']
        pending_tasks_info = [
            {
                'task_id': t.get('task_id'),
                'agent_type': t.get('agent_type'),
                'description': t.get('description'),
                'priority': int(t.get('priority', 999)) if t.get('priority') else 999
            }
            for t in pending_tasks
        ]

        prompt = f"""Re-evaluate investigation workflow based on findings.

Investigation ID: {investigation_id}

CRITICAL CONSTRAINT: Total tasks created: {total_tasks}/{MAX_TASKS_PER_INVESTIGATION}
- If total tasks >= {MAX_TASKS_PER_INVESTIGATION}: MUST conclude immediately
- Remaining task budget: {MAX_TASKS_PER_INVESTIGATION - total_tasks}

Current Context:
- Status: {context.get('status')}
- Confidence: {float(context.get('confidence', 0))}
- Hypothesis: {context.get('current_hypothesis')}
- Findings: {json.dumps(context.get('findings', {}), indent=2, default=str)}
- Timeline: {json.dumps(context.get('timeline', []), indent=2, default=str)}

Current Workflow:
- Completed Tasks: {completed}
- Pending Tasks: {pending}
- Pending Task Details: {json.dumps(pending_tasks_info, indent=2, default=str)}

REQUIRED ACTIONS:
1. Call update_confidence() with your assessment
2. Optionally update/add/remove tasks
3. IF pending tasks > 0: MUST call trigger_investigation("{investigation_id}")

Based on findings, you can:
1. Remove unhelpful pending tasks with remove_pending_tasks
2. Add new high-priority tasks with add_tasks_to_workflow (use specific resource names from findings)
3. Keep existing tasks if they're still relevant

Evaluate the findings and decide next steps."""
        
        response = self.evaluator_agent(prompt)
        log("brain-evaluate", "Evaluation complete", investigation_id=investigation_id)
        
        # Automatically trigger execution if pending tasks exist
        pending_tasks = [t for t in workflow.get('tasks', []) if t.get('status') == 'PENDING']
        
        if pending_tasks:
            log("brain-evaluate", f"Found {len(pending_tasks)} pending tasks, triggering execution", investigation_id=investigation_id)
            
            from aiops.utils.sqs_helper import send_execution_message
            # Get the next pending task ID (first in pending list)
            next_task = pending_tasks[0].get('task_id', 'none')
            send_execution_message(investigation_id, next_task)
        else:
            log("brain-evaluate", "No pending tasks, investigation complete", investigation_id=investigation_id)
            self.context_store.update_status(investigation_id, "COMPLETED")
        
        return f"Re-evaluation complete for {investigation_id}"
