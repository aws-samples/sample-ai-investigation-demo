"""
Decision node for AIOps workflow
"""

from typing import Dict, Any
from langchain_core.messages import AIMessage
import sys
import os
import json

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import centralized logging
from logging_config import get_node_logger

# Import constants
from constants import ContextKeys, AnalysisKeys

# Import the new AI agent node
from nodes.ai_agent_node import AIAgentNode
from util import COMMON_TOOLS

# Import test data export decorator
from test_data_decorator import export_test_data

@export_test_data("decision")
def decision_node(state: Dict[str, Any]):
    """
    Node for making initial decisions about the alert and routing to appropriate agents.
    
    Input:
    - messages: List of message objects containing user input
      The last message is expected to contain the alarm_analysis JSON from the alarm_analyzer_node
    
    Output:
    - messages: Updated with AI response containing decision analysis
    - context: Updated with alarm_analysis object
    """
    # Get trace ID from context if available, fallback to current trace
    trace_id = state.get("context", {}).get("trace_id")
    if not trace_id:
        from trace_context import get_current_trace_id
        trace_id = get_current_trace_id()
    
    # Initialize trace-aware logger with explicit trace ID
    logger = get_node_logger("decision", trace_id=trace_id)
    
    # Log input state for debugging
    logger.info(f"\n=== DECISION_NODE INPUT ===")
    logger.info(f"Messages: {state.get('messages', [])[-1].content if state.get('messages') else 'No messages'}")
    logger.info(f"Context: {json.dumps(state.get('context', {}), indent=2)}")
    
    # Initialize context if not present
    context = state.get("context", {}).copy()
    
    # Extract the alarm_analysis from the last message
    alarm_analysis = {}
    if state["messages"]:
        last_message = state["messages"][-1]
        if hasattr(last_message, "content"):
            message_content = last_message.content
            try:
                # Try to parse the message content as JSON
                alarm_analysis = json.loads(message_content)
                logger.info(f"Successfully parsed alarm_analysis from message content")
            except json.JSONDecodeError:
                logger.info(f"Warning: Could not parse message content as JSON")
        elif isinstance(last_message, dict) and "content" in last_message:
            try:
                # Try to parse the message content as JSON
                alarm_analysis = json.loads(last_message["content"])
                logger.info(f"Successfully parsed alarm_analysis from message content")
            except json.JSONDecodeError:
                logger.info(f"Warning: Could not parse message content as JSON")
    
    # If no alarm_analysis in message, check context for alarm_analysis or cloudwatch_alarm
    if not alarm_analysis:
        if ContextKeys.ALARM_ANALYSIS in context:
            # Use alarm_analysis directly from context
            alarm_analysis = context[ContextKeys.ALARM_ANALYSIS]
            logger.info(f"Using alarm_analysis from context")
        elif "cloudwatch_alarm" in context:
            try:
                # Try to parse the cloudwatch_alarm as JSON
                cloudwatch_data = json.loads(context["cloudwatch_alarm"])
                
                # Extract resource information from dimensions
                resource_info = {}
                if "Dimensions" in cloudwatch_data:
                    for dimension in cloudwatch_data.get("Dimensions", []):
                        if "name" in dimension and "value" in dimension:
                            resource_info[dimension["name"]] = dimension["value"]
                
                # Create an alarm_analysis structure from the cloudwatch data
                alarm_analysis = {
                    "identified_alarm_types": [cloudwatch_data.get("AlarmName", "")],
                    "severity": "High",  # Default to High for CloudWatch alarms
                    "extracted_info": {
                        "alarm_name": cloudwatch_data.get("AlarmName", ""),
                        "alarm_start_time": cloudwatch_data.get("StateChangeTime", ""),
                        "related_resources": [
                            {
                                "resource_id": resource_info.get("InstanceId", resource_info.get("DBInstanceIdentifier", "")),
                                "resource_type": f"AWS::{cloudwatch_data.get('Namespace', '').split('/')[-1]}",
                                "resource_name": cloudwatch_data.get("AlarmDescription", "")
                            }
                        ],
                        "region": cloudwatch_data.get("Region", ""),
                        "account_id": cloudwatch_data.get("AWSAccountId", ""),
                        "metric_details": {
                            "namespace": cloudwatch_data.get("Namespace", ""),
                            "metric_name": cloudwatch_data.get("MetricName", ""),
                            "threshold": cloudwatch_data.get("Threshold", ""),
                            "current_value": cloudwatch_data.get("NewStateValue", ""),
                            "period": f"{cloudwatch_data.get('Period', '')} seconds"
                        }
                    },
                    "possible_causes": [],
                    "additional_info": {
                        "trace_search_criteria": "",
                        "related_services": [cloudwatch_data.get("Namespace", "").split("/")[-1], "CloudWatch"],
                        "recommended_metrics_to_check": []
                    }
                }
                logger.info(f"Created alarm_analysis from cloudwatch_alarm")
            except json.JSONDecodeError as e:
                logger.info(f"Warning: Could not parse cloudwatch_alarm as JSON: {e}")
    
    # Extract user message if available
    user_message = ""
    if len(state["messages"]) > 1:
        prev_message = state["messages"][-2]
        if hasattr(prev_message, "content"):
            user_message = prev_message.content
        elif isinstance(prev_message, dict) and "content" in prev_message:
            user_message = prev_message["content"]
    
    # Prepare input data for the AI agent
    decision_input = {
        "user_message": user_message,
        "alarm_analysis": alarm_analysis,
        "trace_id": trace_id
    }
    
    # Store the input in context for the AIAgentNode
    context[ContextKeys.INITIAL_DECISION] = decision_input
    
    # Update the state with the modified context
    state["context"] = context
    
    # Debug logging to verify context is set
    logger.info(f"Context keys before AIAgentNode: {list(state['context'].keys())}")
    logger.info(f"INITIAL_DECISION key exists: {ContextKeys.INITIAL_DECISION in state['context']}")
    
    # Create the AIAgentNode for decision making with external configuration
    decision_agent = AIAgentNode(
        config={
            "agent_name": "decision"
            # model_id and max_tokens will be loaded from config/nodes.yaml
        },
        prompt_file="decision_prompt.txt",
        context_key=ContextKeys.INITIAL_DECISION,
        tools=COMMON_TOOLS
    )
    
    # Run the decision agent
    try:
        result_state = decision_agent.run(state)
        logger.info("Decision agent completed successfully")
        
        # Extract the decision data from the result
        decision_data = result_state["context"].get(ContextKeys.INITIAL_DECISION, {})
        
    except Exception as e:
        logger.error(f"Error invoking decision agent: {e}", exc_info=True)
        # Create a fallback decision
        decision_data = {
            "alert_type": "Unknown",
            "resource_type": "Unknown",
            "severity": alarm_analysis.get("severity", "Medium"),
            "recommended_path": "resource",
            "reasoning": f"Decision agent failed: {str(e)}"
        }
        result_state = {
            "messages": [AIMessage(content=json.dumps(decision_data, indent=2))],
            "context": state["context"]
        }
    
    # Ensure we preserve critical information from the alarm_analysis
    if not decision_data.get("severity") and alarm_analysis.get("severity"):
        decision_data["severity"] = alarm_analysis["severity"]
    
    # If resource_type is not specified, try to get it from alarm_analysis
    if decision_data.get("resource_type") == "Unknown" and alarm_analysis.get("extracted_info", {}).get("related_resources"):
        resources = alarm_analysis["extracted_info"]["related_resources"]
        if resources and resources[0].get("resource_type"):
            decision_data["resource_type"] = resources[0]["resource_type"]
    
    # Create a combined response that includes both the decision and key alarm information
    combined_response = {
        "decision": decision_data,
        "alarm_summary": {
            "name": alarm_analysis.get("extracted_info", {}).get("alarm_name", "Unknown"),
            "resource": alarm_analysis.get("extracted_info", {}).get("related_resources", [{}])[0].get("resource_id", "Unknown"),
            "resource_type": alarm_analysis.get("extracted_info", {}).get("related_resources", [{}])[0].get("resource_type", "Unknown"),
            "metric": alarm_analysis.get("extracted_info", {}).get("metric_details", {}).get("metric_name", "Unknown"),
            "current_value": alarm_analysis.get("extracted_info", {}).get("metric_details", {}).get("current_value", "Unknown"),
            "threshold": alarm_analysis.get("extracted_info", {}).get("metric_details", {}).get("threshold", "Unknown")
        }
    }
    
    # Update the context with our decision and the alarm analysis
    # Note: routing_function now reads from messages, but downstream nodes still use context for convenience
    result_state["context"][ContextKeys.ALARM_ANALYSIS] = alarm_analysis
    result_state["context"][ContextKeys.INITIAL_DECISION] = decision_data
    
    # Create a JSON response for downstream nodes
    json_response = json.dumps(combined_response, indent=2)
    
    # Ensure trace_id is preserved in the output context
    if trace_id:
        result_state["context"]["trace_id"] = trace_id
    
    # Update the messages with the combined response
    result_state["messages"] = [AIMessage(content=json_response)]
    
    # Log output state for debugging
    logger.info(f"\n=== DECISION_NODE OUTPUT ===")
    logger.info(f"Messages: {result_state['messages'][0].content if result_state['messages'] else 'No messages'}")
    logger.info(f"Context keys: {list(result_state['context'].keys())}")
    logger.info(f"Context: {json.dumps(result_state['context'], indent=2)}")
    
    return result_state
