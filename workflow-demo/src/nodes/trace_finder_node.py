"""
Trace finder node for AIOps workflow
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
from agents.trace_finder_agent import TraceFinderAgent

def trace_finder_node(state: Dict[str, Any]):
    """
    Node for finding and analyzing trace and log data related to the issue.
    
    Input:
    - messages: List of message objects, last message should contain JSON from decision_node with:
      - decision: Decision analysis data (parsed into initial_decision for processing)
      - alarm_summary: Summary of alarm information
    - context: structured JSON containing contextual information from previous nodes
      - alarm_analysis: Alarm analysis from alarm analyzer node
    
    Output:
    - messages: Updated with structured JSON response containing:
        - trace_analysis: structured JSON with the following
            - trace: List of problematic trace summaries
            - metrics: list of facts of the trace node, e.g. 4xx, 5xx, latency, etc.
        - raw_analysis: Summary of root cause analysis
        - relevant_resources: List of resources involved in the trace
    - context: Updated context with input messages from decision node
    """
    # Get trace ID from context if available, fallback to current trace
    trace_id = state.get("context", {}).get("trace_id")
    if not trace_id:
        from trace_context import get_current_trace_id
        trace_id = get_current_trace_id()
    
    # Initialize trace-aware logger with explicit trace ID
    logger = get_node_logger("trace_finder", trace_id=trace_id)
    
    # Log input state for debugging
    logger.info(f"\n=== TRACE_FINDER_NODE INPUT ===")
    logger.info(f"Messages: {state.get('messages', [])[-1].content if state.get('messages') else 'No messages'}")
    logger.info(f"Context: {json.dumps(state.get('context', {}), indent=2)}")
    
    # Get context from previous nodes
    context = state.get("context", {})
    alarm_analysis = context.get(ContextKeys.ALARM_ANALYSIS, {})
    
    # Parse initial_decision from input messages (from decision_node)
    initial_decision = {}
    if state["messages"]:
        try:
            last_message = state["messages"][-1]
            message_content = ""
            if hasattr(last_message, "content"):
                message_content = last_message.content
            elif isinstance(last_message, dict) and "content" in last_message:
                message_content = last_message["content"]
            
            # Parse JSON from decision_node
            if message_content:
                parsed_message = json.loads(message_content)
                initial_decision = parsed_message.get("decision", {})
                logger.info(f"Parsed initial_decision from input message: {initial_decision.get('alert_type', 'Unknown')}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not parse initial_decision from input message: {e}")
            initial_decision = {}
    
    # Add initial_decision to context for this node's processing
    context[ContextKeys.INITIAL_DECISION] = initial_decision
    
    logger.info(f"Initial decision: {initial_decision.get('alert_type', 'Unknown')} - {initial_decision.get('severity', 'Medium')}")
    logger.info(f"Alarm analysis available: {'Yes' if alarm_analysis else 'No'}")
    
    # Extract the content from the message object for processing
    message_content = ""
    if state["messages"]:
        last_message = state["messages"][-1]
        if hasattr(last_message, "content"):
            message_content = last_message.content
        elif isinstance(last_message, dict) and "content" in last_message:
            message_content = last_message["content"]
    
    logger.info(f"Processing message content length: {len(message_content)} characters")
    
    logger.info("Initializing trace finder agent with Bedrock model")
    
    # Initialize the Trace Finder Agent
    agent = TraceFinderAgent()
    
    # Enhance the prompt with initial decision context and alarm analysis
    enhanced_input = message_content
    if initial_decision:
        enhanced_input += f"\n\nInitial Analysis:\n- Alert Type: {initial_decision.get('alert_type', 'Unknown')}\n- Resource Type: {initial_decision.get('resource_type', 'Unknown')}\n- Severity: {initial_decision.get('severity', 'Medium')}"
        logger.info(f"Enhanced input with initial decision: {initial_decision.get('alert_type', 'Unknown')}")
    
    if alarm_analysis:
        enhanced_input += f"\n\nAlarm Analysis:\n{alarm_analysis.get('raw_analysis', 'No alarm analysis available')}"
        logger.info("Enhanced input with alarm analysis data")
    
    logger.info(f"Enhanced input length: {len(enhanced_input)} characters")
    
    try:
        logger.info("Invoking trace finder agent...")
        # Invoke the agent
        response = agent.process(f"Analyze this alert for potential trace and log issues: {enhanced_input}")
        
        logger.info("Trace finder agent completed successfully")
        logger.info(f"Agent response length: {len(response)} characters")
        
    except Exception as e:
        logger.error(f"Error invoking trace finder agent: {e}", exc_info=True)
        # Create a proper JSON error response instead of plain string
        error_response = {
            "trace_analysis": {
                "trace": [],
                "metrics": [],
                "error": f"Error in trace analysis: {str(e)}"
            },
            "raw_analysis": f"Trace analysis failed: {str(e)}",
            "relevant_resources": []
        }
        response = json.dumps(error_response, indent=2)
    
    # Update context with trace analysis only
    # Note: trace_analysis is this node's output, downstream nodes will add it to their context
    trace_analysis_data = response
    
    # Each node should parse what it needs from input messages
    output_context = {
        ContextKeys.ALARM_ANALYSIS: context.get(ContextKeys.ALARM_ANALYSIS, {}),  # Pass through alarm_analysis
        ContextKeys.INITIAL_DECISION: initial_decision,  # Keep initial_decision for this node's context
    }
    
    logger.info("Updated context with trace analysis data")
    
    # Create a structured JSON response for downstream nodes
    combined_response = {
        ContextKeys.TRACE_ANALYSIS: json.loads(trace_analysis_data),
        "alarm_summary": {
            "alert_type": initial_decision.get("alert_type", "Unknown"),
            "resource_type": initial_decision.get("resource_type", "Unknown"),
            "severity": initial_decision.get("severity", "Medium")
        }
    }
    
    # Create JSON response for downstream nodes
    json_response = json.dumps(combined_response, indent=2)
    # Ensure trace_id is preserved in the output context
    if trace_id:
        output_context["trace_id"] = trace_id
    
    output_state = {
        "messages": [AIMessage(content=json_response)],
        "context": output_context
    }
    
    # Log output state for debugging
    logger.info(f"\n=== TRACE_FINDER_NODE OUTPUT ===")
    logger.info(f"Messages: {output_state['messages'][0].content if output_state['messages'] else 'No messages'}...")
    logger.info(f"Context keys: {list(output_state['context'].keys())}")
    logger.info(f"Context: {json.dumps(output_state['context'], indent=2)}")
    logger.info(f"JSON response length: {len(json_response)} characters")
    logger.info("Note: initial_decision not in output context - downstream nodes should parse from messages")
    
    return output_state
