"""Evaluator Agent for post-investigation validation."""

import os
import json
from strands import Agent
from strands.models import BedrockModel
from aiops.utils.context_store import InvestigationContextStore
from aiops.utils.dynamodb_helper import InvestigationStore
from aiops.utils.online_logger import log
from aiops.tools.mcp_client import create_gateway_mcp_client
from aiops.tools.gateway_config import get_gateway_url

class EvaluatorAgent:
    """Evaluator Agent validates investigation results and alerts if needed."""
    
    def __init__(self):
        self.model = BedrockModel(model_id="apac.anthropic.claude-sonnet-4-20250514-v1:0")
        self.context_store = InvestigationContextStore()
        self.store = InvestigationStore()
    
    def evaluate_investigation(self, investigation_id: str) -> dict:
        """Evaluate completed investigation and alert if concerns found.
        
        Args:
            investigation_id: Investigation ID
            
        Returns:
            Evaluation result
        """
        log("evaluator-start", f"Evaluating investigation {investigation_id}", investigation_id=investigation_id)
        print(f"🔍 Evaluating investigation: {investigation_id}")
        
        try:
            # Get investigation context and workflow
            context = self.context_store.get_context(investigation_id)
            workflow = self.store.get_workflow(investigation_id)
            
            if not context or not workflow:
                log("evaluator-error", "Context or workflow not found", level="ERROR", investigation_id=investigation_id)
                return {"status": "error", "error": "Investigation data not found"}
            
            # Load notification tools
            gateway_url = get_gateway_url("notification-gateway")
            if not gateway_url:
                log("evaluator-error", "Notification gateway not configured", level="ERROR", investigation_id=investigation_id)
                return {"status": "error", "error": "Notification gateway not configured"}
            
            mcp_client = create_gateway_mcp_client(gateway_url)
            
            with mcp_client:
                tools = mcp_client.list_tools_sync()
                
                # Build evaluation prompt
                prompt = f"""Evaluate this completed investigation for quality and completeness.

Investigation ID: {investigation_id}

Alarm Summary:
{json.dumps(workflow.get('alarm_summary', {}), indent=2)}

Investigation Status: {context.get('status')}
Confidence: {context.get('confidence')}
Hypothesis: {context.get('current_hypothesis')}

Findings:
{json.dumps(context.get('findings', {}), indent=2)}

Timeline:
{json.dumps(context.get('timeline', []), indent=2)}

Your task:
1. Evaluate if the root cause analysis is complete and convincing
2. Check if there is sufficient evidence to support the conclusion
3. Identify any gaps or inconsistencies in the investigation
4. If you find significant concerns, use the notification tool to alert the on-call team

IMPORTANT: If you have concerns about the investigation quality, call the notification tool directly with a clear warning message."""
                
                agent = Agent(
                    model=self.model,
                    tools=tools,
                    system_prompt="""You are an investigation quality evaluator.

Your role is to validate completed investigations and identify potential issues.
If you find significant concerns, use the available notification tool to alert the on-call team.

Be critical but fair. Only send alerts for significant concerns that require human attention."""
                )
                
                response = agent(prompt)
                
                log("evaluator-complete", f"Evaluation completed for {investigation_id}", investigation_id=investigation_id)
                print(f"✅ Evaluation completed")
                
                return {
                    "status": "completed",
                    "investigation_id": investigation_id,
                    "response": str(response)
                }
            
        except Exception as e:
            log("evaluator-error", f"Error evaluating investigation: {e}", level="ERROR", investigation_id=investigation_id)
            print(f"❌ Error evaluating investigation: {e}")
            return {
                "status": "error",
                "investigation_id": investigation_id,
                "error": str(e)
            }
