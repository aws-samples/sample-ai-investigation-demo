"""Executor Agent for sequential task execution."""

import os
import boto3
import json
import re
from datetime import datetime
from botocore.config import Config
from strands import Agent
from strands.models import BedrockModel
from aiops.tools.storage_tools import get_alarm_summary, store_task_findings, get_investigation_summary
from aiops.utils.dynamodb_helper import InvestigationStore
from aiops.utils.context_store import InvestigationContextStore
from aiops.utils.online_logger import log
from aiops.models.enums import MessageType
from aiops.tools import load_tools_for_agent
from aiops.agents.agent_configs import get_system_prompt, process_agent_result

class ExecutorAgent:
    """Executor Agent executes investigation tasks sequentially."""
    
    def __init__(self):
        self.store = InvestigationStore()
        self.context_store = InvestigationContextStore()
        self.sqs = boto3.client('sqs')
        
        # Use smaller max_tokens to reduce streaming time
        self.model = BedrockModel(
            model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0"
        )
    
    def execute_workflow(self, investigation_id: str) -> dict:
        """Execute workflow for an investigation.
        
        Args:
            investigation_id: Investigation ID
            
        Returns:
            Execution summary
        """
        log("executor-start", f"Starting workflow execution: {investigation_id}", investigation_id=investigation_id)
        print(f"🚀 Starting workflow execution: {investigation_id}")
        
        try:
            # Get next task from DynamoDB
            task = self.store.get_next_task(investigation_id)
            
            if not task:
                log("executor-complete", "No pending tasks - completing investigation", investigation_id=investigation_id)
                self.context_store.update_status(investigation_id, "COMPLETED")
                print("✅ Investigation completed - no pending tasks")
                return {"status": "completed", "investigation_id": investigation_id}
            
            log("executor-execute", f"Executing task {task['task_id']} with {task['agent_type']}", investigation_id=investigation_id)
            print(f"📋 Executing task: {task['task_id']}")
            print(f"   Agent: {task['agent_type']}")
            print(f"   Description: {task['description']}")
            
            # Execute task with tools and context
            result = self.execute_task(task, investigation_id)
            
            log("executor-execute", f"Task {task['task_id']} executed", investigation_id=investigation_id)
            
            # Findings are already stored via store_task_findings tool
            # Just add timeline event
            agent_type = task['agent_type']
            task_id = task['task_id']
            self.context_store.add_timeline_event(
                investigation_id,
                f"Task {task_id} completed by {agent_type}",
                agent_type
            )
            print(f"✅ Task {task_id} completed")
            
            # RootCauseAnalysisAgent completes investigation - no re-evaluation needed
            if agent_type == "RootCauseAnalysisAgent":
                self.store.complete_task(investigation_id, task['task_id'], result)
                log("executor-complete", "RCA completed - investigation finished", investigation_id=investigation_id)
                self.context_store.update_status(investigation_id, "COMPLETED")
                return {
                    "status": "investigation_completed",
                    "investigation_id": investigation_id,
                    "task_id": task['task_id'],
                    "result": result
                }
            
            # Mark complete in DynamoDB (moved here to be last operation before RE_EVALUATE)
            self.store.complete_task(investigation_id, task['task_id'], result)
            log("executor-complete", f"Task {task['task_id']} completed", investigation_id=investigation_id)
            print(f"✅ Task {task['task_id']} completed")
            
            return {
                "status": "completed",
                "investigation_id": investigation_id,
                "task_id": task['task_id'],
                "result": result
            }
        except Exception as e:
            log("executor-error", f"Error executing workflow: {e}", level="ERROR", investigation_id=investigation_id)
            print(f"❌ Error executing workflow: {e}")
            
            # Mark task as failed (current_task stays the same for Brain to decide)
            task_id = task.get('task_id', 'unknown') if 'task' in locals() else 'unknown'
            if task_id != 'unknown':
                self.store.mark_task_failed(investigation_id, task_id, str(e))
                log("executor-error", f"Task {task_id} marked as FAILED", investigation_id=investigation_id)
            
            return {
                "status": "error",
                "investigation_id": investigation_id,
                "task_id": task_id,
                "error": str(e)
            }
        finally:
            # Always send RE_EVALUATE unless it's RootCauseAnalysisAgent (which returns early)
            print(f"🔍 Finally block: agent_type in locals = {'agent_type' in locals()}")
            if 'agent_type' in locals():
                print(f"🔍 agent_type = {agent_type}")
            if 'task_id' in locals():
                print(f"🔍 task_id = {task_id}")
                
            if 'agent_type' in locals() and agent_type != "RootCauseAnalysisAgent":
                from aiops.utils.sqs_helper import send_evaluation_message
                task_id_val = task_id if 'task_id' in locals() else None
                send_evaluation_message(investigation_id, task_id_val)
                log("executor-complete", "Re-evaluation message sent to Brain Agent", investigation_id=investigation_id)
                print(f"✅ Re-evaluation message sent to Brain Agent")
    
    def execute_task(self, task: dict, investigation_id: str) -> dict:
        """Execute a single task using appropriate agent with tools.
        
        Args:
            task: Task dict with agent_type and description
            investigation_id: Investigation ID for context loading
            
        Returns:
            Task execution result
        """
        agent_type = task['agent_type']
        description = task['description']
        
        try:
            from aiops.tools.mcp_client import create_gateway_mcp_client
            from aiops.tools.gateway_config import get_gateways_for_agent, get_gateway_url
            
            # Load alarm summary for context
            alarm_summary = self.store.get_workflow(investigation_id).get('alarm_summary', {})
            task_id = task.get('task_id', 'unknown')
            context = f"Investigation ID: {investigation_id}\nTask ID: {task_id}\n\nAlarm Context: {alarm_summary}\n\nTask: {description}"
            
            # Get gateway for this agent
            gateway_names = get_gateways_for_agent(agent_type)
            if not gateway_names:
                return {"status": "error", "error": f"No gateway configured for {agent_type}"}
            
            gateway_name = gateway_names[0]
            gateway_url = get_gateway_url(gateway_name)
            
            print(f"🔧 Connecting to gateway: {gateway_name}")
            mcp_client = create_gateway_mcp_client(gateway_url)
            
            # Keep MCP client session open during execution
            with mcp_client:
                # Load tools within context
                tools = [get_alarm_summary, store_task_findings, get_investigation_summary]
                pagination_token = None
                while True:
                    result = mcp_client.list_tools_sync(pagination_token=pagination_token)
                    tools.extend(result)
                    if result.pagination_token is None:
                        break
                    pagination_token = result.pagination_token
                
                print(f"✅ Loaded {len(tools)} tools")
                
                # Create and execute agent within context
                print(f"🤖 Creating agent...")
                system_prompt = get_system_prompt(agent_type, investigation_id)
                system_prompt += f"\n\nYour Task ID: {task_id} - Use this when calling store_task_findings"
                system_prompt += "\n\nIMPORTANT: Return ONLY valid JSON in the specified format. No additional text before or after the JSON."
                agent = Agent(
                    model=self.model,
                    tools=tools,
                    system_prompt=system_prompt
                )
                
                print(f"▶️  Executing agent with context...")
                response = agent(context)
                print(f"✅ Agent execution completed")
                
                # Extract message from response
                if hasattr(response, 'message'):
                    message = response.message
                else:
                    message = str(response)
                
                # If message is already a dict, return it directly
                if isinstance(message, dict):
                    return {
                        "status": "completed",
                        **message
                    }
                
                # Try to extract JSON from string message
                import re
                json_match = re.search(r'\{.*\}', message, re.DOTALL)
                if json_match:
                    try:
                        parsed_result = json.loads(json_match.group())
                        return {
                            "status": "completed",
                            "message": message,
                            **parsed_result
                        }
                    except json.JSONDecodeError:
                        pass
                
                return {
                    "status": "completed",
                    "message": message
                }
                
        except Exception as e:
            import traceback
            print(f"❌ Error executing task: {e}")
            print(f"📍 Traceback: {traceback.format_exc()[-500:]}")
            return {
                "status": "error",
                "error": str(e)
            }
