"""
Logs collector node for AIOps workflow
"""

from typing import Dict, Any
from langchain_core.messages import AIMessage
import sys
import os
import json

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import get_bedrock_model, create_prompt_template, create_agent_executor, COMMON_TOOLS
from agents.logs_collector_agent import LogsCollectorAgent

# Import centralized logging
from logging_config import get_node_logger

# Import constants
from constants import ContextKeys, AnalysisKeys

def logs_collector_node(state: Dict[str, Any]):
    """
    Node for collecting and summarizing logs related to the incident.
    
    Input:
    - messages: List of message objects containing previous analysis results
    - context: Dict containing contextual information from previous nodes
      - alarm_analysis: Alarm analysis from alarm analyzer node
      - initial_decision: Decision analysis from decision node
      - trace_analysis: Trace analysis from trace finder node (if trace path)
      - domain_analysis: Domain analysis from domain bot node (if resource path)
      - resource_info: Resource information from resource collector node (if resource path)
    
    Output:
    - messages: Updated with AI response containing logs collection analysis in JSON format
      - logs: List of relevant logs information from CloudWatch logs with the following attributes in each item
        - resource_info: Information about the resource in json format
        - logs: List of top 50 summarized log entries related to the resource
    - context: Updated context with logs data information
      - logs_data: Dict containing summarized logs information
    """
    # Get trace ID from context if available, fallback to current trace
    trace_id = state.get("context", {}).get("trace_id")
    if not trace_id:
        from trace_context import get_current_trace_id
        trace_id = get_current_trace_id()
    
    # Initialize trace-aware logger with explicit trace ID
    logger = get_node_logger("logs_collector", trace_id=trace_id)
    
    # Log input state for debugging
    logger.info(f"\n=== LOGS_COLLECTOR_NODE INPUT ===")
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
    
    logger.info(f"Initial decision available: {'Yes' if initial_decision else 'No'}")
    logger.info(f"Alarm analysis available: {'Yes' if alarm_analysis else 'No'}")
    logger.info(f"Trace graph analysis available: {'Yes' if trace_graph_analysis else 'No'}")
    logger.info(f"Trace analysis available: {'Yes' if trace_analysis else 'No'}")
    logger.info(f"Domain analysis available: {'Yes' if domain_analysis else 'No'}")
    logger.info(f"Resource info available: {'Yes' if resource_info else 'No'}")
    
    # Extract the content from the message object
    message_content = ""
    if state["messages"]:
        last_message = state["messages"][-1]
        if hasattr(last_message, "content"):
            message_content = last_message.content
        elif isinstance(last_message, dict) and "content" in last_message:
            message_content = last_message["content"]
    
    logger.info(f"Processing message content length: {len(message_content)} characters")
    
    logger.info("Initializing logs collector agent with Bedrock model")
    
    # Initialize the Logs Collector Agent
    agent = LogsCollectorAgent()
    
    # Build a comprehensive context for the logs collector
    enhanced_input = json.loads(message_content)
    enhanced_input[ContextKeys.ALARM_ANALYSIS] = alarm_analysis
    # enhanced_input[ContextKeys.INITIAL_DECISION] = initial_decision
    # enhanced_input[ContextKeys.TRACE_GRAPH_ANALYSIS] = trace_graph_analysis
    enhanced_input[ContextKeys.TRACE_ANALYSIS] = trace_graph_analysis
    # enhanced_input["domain_analysis"] = domain_analysis
    enhanced_input["resource_info"] = resource_info
    # enhanced_input["trace_id"] = trace_id
    
    
    
    logger.info(f"Context summary items: {len(enhanced_input)}")
    
    try:
        logger.info("Invoking logs collector agent...")
        
        # Invoke the agent
        response = agent.process(f"{enhanced_input}")
        
        logger.info("Logs collector agent completed successfully")
        logger.info(f"Agent response length: {len(response)} characters")
        
    except Exception as e:
        logger.error(f"Error invoking logs collector agent: {e}", exc_info=True)
        # Create a proper JSON error response instead of plain string
        error_response = {
            "log_analysis": {
                "logs": [],
                "metrics": [],
                "patterns": [],
                "error": f"Error in logs collection: {str(e)}"
            },
            "raw_analysis": f"Logs collection failed: {str(e)}"
        }
        response = json.dumps(error_response, indent=2)
        
    logger.info("Updated context with logs data structure")
    
    # Ensure trace_id is preserved in the output context
    if trace_id:
        context["trace_id"] = trace_id
    
    context[ContextKeys.TRACE_RESOURCES] = json.loads(message_content)

    output_state = {
        "messages": [AIMessage(content=response)],
        "context": context
    }
    
    # Log output state for debugging
    logger.info(f"\n=== LOGS_COLLECTOR_NODE OUTPUT ===")
    logger.info(f"Messages: {output_state['messages'][0].content[:200] if output_state['messages'] else 'No messages'}...")
    logger.info(f"Context logs_data keys: {list(output_state['context'].keys())}")
    logger.info(f"Logs data categories: {len(output_state['context'])}")
    
    return output_state
