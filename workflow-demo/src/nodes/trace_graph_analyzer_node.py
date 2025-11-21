"""
Trace graph analyzer node for AIOps workflow
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

# Import the new AI agent node directly
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nodes'))
from ai_agent_node import AIAgentNode

from util import COMMON_TOOLS

# Import the X-Ray service graph tools
from tools.xray_service_graph_tool import get_xray_service_graph, analyze_xray_service_graph

# Import test data export decorator
from test_data_decorator import export_test_data

@export_test_data("trace_graph_analyzer")
def trace_graph_analyzer_node(state: Dict[str, Any]):
    """
    Node for analyzing trace graph and finding most relevant trace nodes.
    
    Input:
    - messages: List of message objects, last message should contain JSON from decision_node with:
      - decision: Decision analysis data (parsed into initial_decision for processing)
      - alarm_summary: Summary of alarm information
    - context: structured JSON containing contextual information from previous nodes
      - alarm_analysis: Alarm analysis from alarm analyzer node
    
    Output:
    - messages: Updated with structured JSON response containing:
        - service_graph: Service graph data from X-Ray
        - relevant_nodes: List of most relevant trace nodes for investigation, each with following attributes:
            - service_name: Name of the service
            - service_type: Type of the service (e.g., AWS::Lambda::Function, AWS::EC2::Instance)
            - error_rate: Error rate for the service in text
            - latency: Average latency for the service in text
            - reason: Reason for relevance (e.g., high error rate, latency)
            - filter_criteria: Filter criteria for getting trace summaries
            - raw_analysis: Summary of trace graph analysis
        - recommended_services: List of services to investigate further
    - context: Updated context with initial decision object
    """
    # Get trace ID from context if available, fallback to current trace
    trace_id = state.get("context", {}).get("trace_id")
    if not trace_id:
        from trace_context import get_current_trace_id
        trace_id = get_current_trace_id()
    
    # Initialize trace-aware logger with explicit trace ID
    logger = get_node_logger("trace_graph_analyzer", trace_id=trace_id)
    
    # Log input state for debugging
    logger.info(f"\n=== TRACE_GRAPH_ANALYZER_NODE INPUT ===")
    logger.info(f"Messages: {state.get('messages', [])[-1].content if state.get('messages') else 'No messages'}")
    logger.info(f"Context: {json.dumps(state.get('context', {}), indent=2)}")
    
    # Get context from previous nodes
    context = state.get("context", {}).copy()
    alarm_analysis = context.get(ContextKeys.ALARM_ANALYSIS, {})
    
    # Parse initial_decision from input messages (from decision_node)
    message_content = ""
    enhanced_input = {}
    
    if state["messages"]:
        try:
            last_message = state["messages"][-1]
            
            if hasattr(last_message, "content"):
                message_content = last_message.content
            elif isinstance(last_message, dict) and "content" in last_message:
                message_content = last_message["content"]
            
            # Parse the JSON content from decision node
            enhanced_input = json.loads(message_content)
            logger.info(f"Successfully parsed decision data from message content")
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Could not parse initial_decision from input message: {e}")
            enhanced_input = {}
    
    # Enhance the input with alarm analysis context
    if alarm_analysis:
        enhanced_input[ContextKeys.ALARM_ANALYSIS] = alarm_analysis
        logger.info("Enhanced input with alarm analysis data")
    
    # Add trace_id to the input
    enhanced_input["trace_id"] = trace_id
    
    # Store the enhanced input in context for the AIAgentNode
    context[ContextKeys.TRACE_GRAPH_ANALYSIS] = enhanced_input
    
    # Update the state with the modified context
    state["context"] = context
    
    logger.info(f"Processing enhanced input with {len(str(enhanced_input))} characters")
    
    # Create X-Ray tools for trace graph analysis
    xray_tools = [get_xray_service_graph, analyze_xray_service_graph]
    all_tools = COMMON_TOOLS + xray_tools
    
    # Create the AIAgentNode for trace graph analysis with external configuration
    trace_graph_agent = AIAgentNode(
        config={
            "agent_name": "trace_graph_analyzer"
            # model_id and max_tokens will be loaded from config/nodes.yaml
        },
        prompt_file="trace_graph_analyzer_prompt.txt",
        context_key=ContextKeys.TRACE_GRAPH_ANALYSIS,
        tools=all_tools
    )
    
    # Run the trace graph analyzer agent
    try:
        logger.info("Invoking trace graph analyzer agent...")
        result_state = trace_graph_agent.run(state)
        logger.info("Trace graph analyzer agent completed successfully")
        
        # Extract the analysis data from the result
        analysis_data = result_state["context"].get(ContextKeys.TRACE_GRAPH_ANALYSIS, {})
        
        # Get the AI response from messages
        if result_state["messages"]:
            ai_response = result_state["messages"][-1].content
            logger.info(f"Agent response length: {len(ai_response)} characters")
        else:
            ai_response = json.dumps({
                "trace_graph_analysis": {
                    "service_graph": [],
                    "relevant_nodes": [],
                    "filter_criteria": ""
                },
                "raw_analysis": "No response from trace graph analyzer",
                "recommended_services": []
            })
        
    except Exception as e:
        logger.error(f"Error invoking trace graph analyzer agent: {e}", exc_info=True)
        # Create a proper JSON error response
        error_response = {
            "trace_graph_analysis": {
                "service_graph": {
                    "root_service_name": "unknown",
                    "root_service_type": "unknown", 
                    "total_services": 0,
                    "total_requests": 0,
                    "error_rate": 0
                },
                "relevant_nodes": [],
                "filter_criteria": ""
            },
            "raw_analysis": f"Trace graph analysis failed: {str(e)}",
            "recommended_services": []
        }
        ai_response = json.dumps(error_response, indent=2)
        result_state = {
            "messages": [AIMessage(content=ai_response)],
            "context": state["context"]
        }
    
    # Ensure trace_id is preserved in the output context
    if trace_id:
        result_state["context"]["trace_id"] = trace_id
    
    # Update the messages with the analysis response
    result_state["messages"] = [AIMessage(content=ai_response)]
    
    # Log output state for debugging
    logger.info(f"\n=== TRACE_GRAPH_ANALYZER_NODE OUTPUT ===")
    logger.info(f"Messages: {result_state['messages'][0].content if result_state['messages'] else 'No messages'}")
    logger.info(f"Context keys: {list(result_state['context'].keys())}")
    logger.info(f"JSON response length: {len(ai_response)} characters")
    
    return result_state
