
from typing import Dict, Any
from nodes.ai_agent_node import AIAgentNode
from constants import ContextKeys
from aws_context_utils import extract_aws_context_from_alarm_data, format_aws_context_summary
from logging_config import get_node_logger

def alarm_analyzer_node(state: Dict[str, Any]):
    logger = get_node_logger("alarm_analyzer")
    
    # Extract the raw alarm data from the initial message
    if "messages" in state and state["messages"]:
        raw_alarm_data = state["messages"][-1].content
    else:
        raise ValueError("Missing initial alarm message in state.")

    # The AIAgentNode expects the input data to be in the context
    state["context"][ContextKeys.ALARM_ANALYSIS] = raw_alarm_data

    # Create the AIAgentNode with external configuration
    alarm_analyzer = AIAgentNode(
        config={
            "agent_name": "alarm_analyzer"
            # model_id and max_tokens will be loaded from config/nodes.yaml
        },
        prompt_file="alarm_analyzer_prompt.txt",
        context_key=ContextKeys.ALARM_ANALYSIS
    )
    
    # Run the node using the decorated function
    result_state = alarm_analyzer.run(state)

    # Extract AWS context from the analysis
    alarm_analysis = result_state["context"].get(ContextKeys.ALARM_ANALYSIS, {})
    region, account_id = extract_aws_context_from_alarm_data(alarm_analysis)

    # Update the context with AWS info
    if region:
        result_state["context"][ContextKeys.REGION] = region
    if account_id:
        result_state["context"][ContextKeys.ACCOUNT_ID] = account_id

    logger.info(f"AWS Context extracted: {format_aws_context_summary(region, account_id)}")

    return result_state
