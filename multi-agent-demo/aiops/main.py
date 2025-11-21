"""AIOps AgentCore Runtime Entry Point"""

from bedrock_agentcore import BedrockAgentCoreApp
from .orchestrator.brain_agent import BrainAgent
from .orchestrator.executor_agent import ExecutorAgent
from .models.enums import MessageType
from .utils.online_logger import log
import json

app = BedrockAgentCoreApp()

@app.entrypoint
def invoke(payload):
    """Route messages to Brain or Executor based on message_type."""
    log("main-invoke", f"RAW PAYLOAD: {json.dumps(payload, default=str)}")
    
    message_type = payload.get("message_type", MessageType.ALARM.value)
    log("main-invoke", f"message_type='{message_type}', EXECUTION='{MessageType.EXECUTION.value}', EVALUATION='{MessageType.EVALUATION.value}'")
    
    if message_type == MessageType.EXECUTION.value:
        log("main-route", "Routing to EXECUTOR")
        investigation_id = payload.get("investigation_id")
        executor = ExecutorAgent()
        result = executor.execute_workflow(investigation_id)
        return {
            "investigation_id": investigation_id,
            "status": "execution_ongoing",
            "result": result
        }
    elif message_type == MessageType.EVALUATION.value:
        log("main-route", "Routing to BRAIN re_evaluate_workflow")
        investigation_id = payload.get("investigation_id")
        brain = BrainAgent()
        result = brain.re_evaluate_workflow(investigation_id)
        return {
            "investigation_id": investigation_id,
            "status": "re_evaluation_complete",
            "result": result
        }
    else:
        log("main-route", f"No match, defaulting to ALARM processing")
        alarm_text = payload.get("alarm", payload.get("prompt", ""))
        brain = BrainAgent()
        investigation_id = brain.process_alarm_text(alarm_text)
        return {
            "investigation_id": investigation_id,
            "status": "investigation_triggered",
            "message": "Workflow created and execution queued"
        }

if __name__ == "__main__":
    app.run()


