"""
Trace details analyzer node for AIOps workflow
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

# Import the agent
from agents.trace_details_analyzer_agent import TraceDetailsAnalyzerAgent

def trace_details_analyzer_node(state: Dict[str, Any]):
    """
    Node for getting trace summaries and aggregating detailed trace information.
    
    Input:
    - messages: List of message objects, last message should contain JSON from trace_graph_analyzer_node with:
      - trace_graph_analysis: Trace graph analysis data with filter criteria
      - alarm_summary: Summary of alarm information
    - context: structured JSON containing contextual information from previous nodes
      - alarm_analysis: Alarm analysis from alarm analyzer node
      - initial_decision: Decision analysis from decision node
      - trace_graph_analysis: Trace graph analysis from trace graph analyzer node
    
    Output:
    - messages: Updated with structured JSON response containing:
        - trace_analysis: structured JSON with the following
            - trace: List of problematic trace summaries with the following attributes in each item:
                - trace_id: Unique identifier for the trace
                - start_time: Start time of the trace
                - findings: List of findings related to the trace, e.g. 4xx, 5xx, latency, etc.
            - metrics: list of facts of the trace node, e.g. 4xx, 5xx, latency, etc.
        - raw_analysis: Summary of root cause analysis
        - relevant_resources: List of resources involved in the trace
    - context: Updated context with input trace graph analysis data
    """
    # Get trace ID from context if available, fallback to current trace
    trace_id = state.get("context", {}).get("trace_id")
    if not trace_id:
        from trace_context import get_current_trace_id
        trace_id = get_current_trace_id()
    
    # Initialize trace-aware logger with explicit trace ID
    logger = get_node_logger("trace_details_analyzer", trace_id=trace_id)
    
    # Log input state for debugging
    logger.info(f"\n=== TRACE_DETAILS_ANALYZER_NODE INPUT ===")
    logger.info(f"Messages: {state.get('messages', [])[-1].content if state.get('messages') else 'No messages'}")
    logger.info(f"Context: {json.dumps(state.get('context', {}), indent=2)}")
    
    # Get context from previous nodes
    context = state.get("context", {})
    alarm_analysis = context.get(ContextKeys.ALARM_ANALYSIS, {})
    initial_decision = context.get(ContextKeys.INITIAL_DECISION, {})
    trace_graph_analysis = context.get(ContextKeys.TRACE_GRAPH_ANALYSIS, {})
    
    # Parse trace_graph_analysis from input messages (from trace_graph_analyzer_node)
    trace_graph_data = {}
    message_content = ""
    parsed_message = {}
    if state["messages"]:
        try:
            last_message = state["messages"][-1]
            
            if hasattr(last_message, "content"):
                message_content = last_message.content
            elif isinstance(last_message, dict) and "content" in last_message:
                message_content = last_message["content"]
            
            # Parse JSON from trace_graph_analyzer_node
            if message_content:
                parsed_message = json.loads(message_content)
                trace_graph_data = parsed_message.get(ContextKeys.TRACE_GRAPH_ANALYSIS, {})
                logger.info(f"Parsed trace_graph_analysis from input message")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not parse trace_graph_analysis from input message: {e}")
            trace_graph_data = {}
    
    logger.info(f"Initial decision available: {'Yes' if initial_decision else 'No'}")
    logger.info(f"Alarm analysis available: {'Yes' if alarm_analysis else 'No'}")
    logger.info(f"Trace graph analysis available: {'Yes' if trace_graph_data else 'No'}")
    logger.info(f"Processing message content length: {len(message_content)} characters")
    
    logger.info("Initializing trace details analyzer agent with Bedrock model")
    # Initialize the Trace Details Analyzer Agent
    agent = TraceDetailsAnalyzerAgent()
    
    # Enhance the prompt with all available context
    enhanced_input = parsed_message
    # enhanced_input[ContextKeys.INITIAL_DECISION] = initial_decision
    # enhanced_input[ContextKeys.ALARM_ANALYSIS] = alarm_analysis
    enhanced_input[ContextKeys.TRACE_GRAPH_ANALYSIS] = trace_graph_data
    
    logger.info(f"Enhanced input length: {len(enhanced_input)} characters")
    
    try:
        logger.info("Invoking trace details analyzer agent...")
        # Invoke the agent
        response = agent.process(f"{enhanced_input}")
        
        logger.info("Trace details analyzer agent completed successfully")
        logger.info(f"Agent response length: {len(response)} characters")
        
    except Exception as e:
        logger.error(f"Error invoking trace details analyzer agent: {e}", exc_info=True)
        # Create a proper JSON error response instead of plain string
        error_response = {
            "trace_analysis": {
                "trace_analysis": {
                    "service": "unknown",
                    "errors": [],
                    "latency": 0
                },
                "raw_analysis": f"Trace details analysis failed: {str(e)}",
                "error": f"Error in trace details analysis: {str(e)}"
            }
        }
        response = json.dumps(error_response, indent=2)
    
    
    # Each node should parse what it needs from input messages
    output_context = {
        ContextKeys.ALARM_ANALYSIS: context.get(ContextKeys.ALARM_ANALYSIS, {}),  # Pass through alarm_analysis
        ContextKeys.INITIAL_DECISION: initial_decision,  # Keep initial_decision for this node's context
        ContextKeys.TRACE_GRAPH_ANALYSIS: trace_graph_data,  # Pass through trace_graph_analysis
    }
    
    logger.info("Updated context with complete trace analysis data")

    
    # Create JSON response for downstream nodes
    json_response = json.dumps(json.loads(response), indent=2)
    
    # Ensure trace_id is preserved in the output context
    if trace_id:
        output_context["trace_id"] = trace_id
    
    output_state = {
        "messages": [AIMessage(content=json_response)],
        "context": output_context
    }
    
    # Log output state for debugging
    logger.info(f"\n=== TRACE_DETAILS_ANALYZER_NODE OUTPUT ===")
    logger.info(f"Messages: {json.loads(output_state['messages'][-1].content) if output_state['messages'] else 'No messages'}...")
    logger.info(f"Context keys: {list(output_state['context'].keys())}")
    logger.info(f"JSON response length: {len(json_response)} characters")
    
    return output_state
