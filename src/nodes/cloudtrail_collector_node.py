"""
CloudTrail collector node for AIOps workflow
"""

from typing import Dict, Any
from nodes.ai_agent_node import AIAgentNode
from constants import ContextKeys
from logging_config import get_node_logger
from util import COMMON_TOOLS
import json

# Define CloudTrail-specific tools
from tools.cloudtrail_changes_tool import get_resource_changes

CLOUDTRAIL_COLLECTOR_TOOLS = COMMON_TOOLS.copy()
CLOUDTRAIL_COLLECTOR_TOOLS.append(get_resource_changes)

def cloudtrail_collector_node(state: Dict[str, Any]):
    """
    Node for collecting CloudTrail events related to the incident.
    
    Input:
    - messages: List of message objects containing previous analysis results
    - context: Dict containing contextual information from previous nodes
      - alarm_analysis: Alarm analysis from alarm analyzer node
      - initial_decision: Decision analysis from decision node
      - trace_analysis: Trace analysis from trace finder node (if trace path)
      - domain_analysis: Domain analysis from domain bot node (if resource path)
      - resource_info: Resource information from resource collector node (if resource path)
      - logs_analysis: Logs data from logs collector node
    
    Output:
    - messages: Updated with AI response containing CloudTrail collection analysis in JSON format
      - cloudtrail_analysis: structured JSON list with the following attributes in each item:
        - resource_info: Information about the resource in json format
        - events: List of CloudTrail events related to the resource
    - context: Updated context with CloudTrail data information
      - cloudtrail_data: Dict containing CloudTrail events and metrics information
    """
    logger = get_node_logger("cloudtrail_collector")
    
    # Get trace ID from context if available, fallback to current trace
    trace_id = state.get("context", {}).get("trace_id")
    if not trace_id:
        from trace_context import get_current_trace_id
        trace_id = get_current_trace_id()
    
    # Log input state for debugging
    logger.info(f"\n=== CLOUDTRAIL_COLLECTOR_NODE INPUT ===")
    logger.info(f"Messages: {state.get('messages', [])[-1].content if state.get('messages') else 'No messages'}")
    logger.info(f"Context: {json.dumps(state.get('context', {}), indent=2)}")
    
    # Get context from previous nodes
    context = state.get("context", {})
    alarm_analysis = context.get(ContextKeys.ALARM_ANALYSIS, {})
    initial_decision = context.get(ContextKeys.INITIAL_DECISION, {})
    trace_graph_analysis = context.get(ContextKeys.TRACE_GRAPH_ANALYSIS, {})
    trace_analysis = context.get(ContextKeys.TRACE_ANALYSIS, {})
    domain_analysis = context.get("domain_analysis", {})
    resource_info = context.get("resource_info", {})
    log_analysis = context.get(ContextKeys.LOGS_ANALYSIS, {})
    
    logger.info(f"Initial decision available: {'Yes' if initial_decision else 'No'}")
    logger.info(f"Alarm analysis available: {'Yes' if alarm_analysis else 'No'}")
    logger.info(f"Trace analysis available: {'Yes' if trace_analysis else 'No'}")
    logger.info(f"Trace graph analysis available: {'Yes' if trace_graph_analysis else 'No'}")
    logger.info(f"Domain analysis available: {'Yes' if domain_analysis else 'No'}")
    logger.info(f"Resource info available: {'Yes' if resource_info else 'No'}")
    logger.info(f"Logs analysis available: {'Yes' if log_analysis else 'No'}")
    
    if initial_decision:
        logger.info(f"Alert type: {initial_decision.get('alert_type', 'Unknown')}, Severity: {initial_decision.get('severity', 'Medium')}")
    
    # Extract the content from the message object and prepare comprehensive input
    message_content = ""
    if state["messages"]:
        last_message = state["messages"][-1]
        if hasattr(last_message, "content"):
            message_content = last_message.content
        elif isinstance(last_message, dict) and "content" in last_message:
            message_content = last_message["content"]
    
    logger.info(f"Processing message content length: {len(message_content)} characters")
    
    # Build a comprehensive context for the CloudTrail collector
    try:
        if message_content and message_content.strip():
            updated_input = json.loads(message_content)
        else:
            updated_input = {}
            logger.warning("Message content is empty, using empty dictionary as base")
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse message content as JSON: {e}")
        updated_input = {"raw_message_content": message_content}
    
    # Add all the context information
    updated_input[ContextKeys.ALARM_ANALYSIS] = alarm_analysis
    updated_input[ContextKeys.INITIAL_DECISION] = initial_decision
    updated_input[ContextKeys.TRACE_GRAPH_ANALYSIS] = trace_graph_analysis
    updated_input[ContextKeys.TRACE_ANALYSIS] = trace_analysis
    updated_input["domain_analysis"] = domain_analysis
    updated_input["resource_info"] = resource_info
    updated_input["trace_id"] = trace_id
    updated_input["log_analysis"] = log_analysis
    
    # Store the comprehensive input in context for the AIAgentNode
    state["context"][ContextKeys.CLOUDTRAIL_ANALYSIS] = updated_input

    # Create the AIAgentNode for CloudTrail collection with external configuration
    cloudtrail_collector = AIAgentNode(
        config={
            "agent_name": "cloudtrail_collector"
            # model_id and max_tokens will be loaded from config/nodes.yaml
        },
        prompt_file="cloudtrail_collector_prompt.txt",
        context_key=ContextKeys.CLOUDTRAIL_ANALYSIS,
        tools=CLOUDTRAIL_COLLECTOR_TOOLS
    )
    
    # Run the node using the decorated function
    try:
        result_state = cloudtrail_collector.run(state)
        logger.info("CloudTrail collector agent completed successfully")
    except Exception as e:
        logger.error(f"Error invoking CloudTrail collector agent: {e}", exc_info=True)
        # Create a proper JSON error response
        error_response = {
            "cloudtrail_analysis": {
                "events": [],
                "metrics": [],
                "config": [],
                "error": f"Error in CloudTrail collection: {str(e)}"
            },
            "raw_analysis": f"CloudTrail collection failed: {str(e)}"
        }
        result_state = {
            "messages": [{"content": json.dumps(error_response, indent=2)}],
            "context": state["context"]
        }

    # Ensure trace_id is preserved in the output context
    if trace_id:
        result_state["context"]["trace_id"] = trace_id
    
    # Log output state for debugging
    logger.info(f"\n=== CLOUDTRAIL_COLLECTOR_NODE OUTPUT ===")
    logger.info(f"Messages: {result_state['messages'][0].content if result_state['messages'] else 'No messages'}")
    logger.info(f"Context keys: {list(result_state['context'].keys())}")
    
    return result_state
