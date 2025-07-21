"""
Root Cause Analysis node for AIOps workflow
This node analyzes all collected data to determine the most likely root cause of an incident.
"""

from typing import Dict, Any, List
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
from util import model_direct_invoke

# Import the agent
from agents.root_cause_analysis_agent import RootCauseAnalysisAgent

def root_cause_analysis_node(state: Dict[str, Any]):
    """
    Node for determining the root cause of an incident based on collected data.
    
    Input:
    - messages: List of message objects containing previous analysis results
    - context: Dict containing contextual information from all previous nodes
      - alarm_analysis: Alarm analysis results
      - resource_info: Resource information (if resource path)
      - log_analysis: Logs data from logs collector
      - cloudtrail_analysis: CloudTrail data from CloudTrail collector
      - trace_analysis: Trace analysis results (if trace path)
      - trace_resources: Trace resource information (if trace path)
      - domain_analysis: Domain-specific analysis (if resource path)
    
    Output:
    - messages: Updated with AI response containing root cause analysis
    - context: Updated with root_cause object containing:
      - identified_cause: Primary cause of the issue
      - confidence_score: Confidence level in the analysis (0.0-1.0)
      - related_factors: Other contributing factors
      - evidence: Supporting evidence for the conclusion
      - recommended_actions: List of recommended actions to resolve the issue
    """
    # Get trace ID from context if available, fallback to current trace
    trace_id = state.get("context", {}).get("trace_id")
    if not trace_id:
        from trace_context import get_current_trace_id
        trace_id = get_current_trace_id()
    
    # Initialize trace-aware logger with explicit trace ID
    logger = get_node_logger("root_cause_analysis", trace_id=trace_id)
    
    # Log input state for debugging
    logger.info(f"\n=== ROOT_CAUSE_ANALYSIS_NODE INPUT ===")
    logger.info(f"Messages: {state.get('messages', [])[-1].content if state.get('messages') else 'No messages'}")
    logger.info(f"Context: {json.dumps(state.get('context', {}), indent=2)}")
    
    # Safely parse message content with error handling
    message = {}
    if state.get('messages') and len(state.get('messages', [])) > 0:
        message_content = state.get('messages', [])[-1].content
        if message_content and message_content.strip():
            try:
                message = json.loads(message_content)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse message content as JSON: {e}")
                logger.warning(f"Message content: {message_content}")
                # Try to extract any JSON-like content or use empty dict
                message = {}
        else:
            logger.warning("Message content is empty or None")
    else:
        logger.warning("No messages found in state")
    
    # Extract context information
    context = state.get("context", {})
    
    # Get all relevant data from the context
    alarm_data = context.get(ContextKeys.ALARM_ANALYSIS, {})
    resource_data = context.get("resource_info", {})
    log_analysis = context.get("log_analysis", {})
    cloudtrail_analysis = context.get("cloudtrail_analysis", {})
    trace_analysis = context.get(ContextKeys.TRACE_ANALYSIS, {})
    trace_graph_analysis = context.get("trace_graph_analysis", {})
    domain_analysis = context.get("domain_analysis", {})
    trace_resources = context.get(ContextKeys.TRACE_RESOURCES, {})
    
    logger.info(f"Alarm data available: {'Yes' if alarm_data else 'No'}")
    logger.info(f"Resource data available: {'Yes' if resource_data else 'No'}")
    logger.info(f"Logs data available: {'Yes' if log_analysis else 'No'}")
    logger.info(f"CloudTrail data available: {'Yes' if cloudtrail_analysis else 'No'}")
    logger.info(f"Trace data available: {'Yes' if trace_analysis else 'No'}")
    logger.info(f"Trace resources available: {'Yes' if trace_resources else 'No'}")
    logger.info(f"Domain analysis available: {'Yes' if domain_analysis else 'No'}")
    
    # Initialize the LLM
    # Initialize the Root Cause Analysis Agent
    agent = RootCauseAnalysisAgent()
    
    # Prepare the input for the agent with all available context data
    input_data = {
        
        ContextKeys.ALARM_ANALYSIS: alarm_data,
        ContextKeys.LOGS_ANALYSIS: log_analysis,
        ContextKeys.CLOUDTRAIL_ANALYSIS: message,
        ContextKeys.TRACE_ANALYSIS: trace_analysis,
        ContextKeys.TRACE_RESOURCES: trace_resources
    }
    
    logger.info(f"Prepared input data with {len([k for k, v in input_data.items() if v])} populated data sources")
    
    try:
        logger.info("Invoking root cause analysis agent...")
        
        # Invoke the agent
        response = agent.process(f"""
Analyze all the collected data to determine the root cause of this incident:

{json.dumps(input_data, indent=2)}

Remember to return your analysis as a valid JSON object with the structure specified in your instructions.
""")
        
        logger.info("Root cause analysis agent completed successfully")
        
        # Extract the root cause analysis from the agent's response
        logger.info(f"Agent response length: {len(response)} characters")
        
    except Exception as e:
        logger.error(f"Error invoking root cause analysis agent: {e}", exc_info=True)
        # Create a proper JSON error response instead of plain string
        error_response = {
            "root_cause_analysis": {
                "root_cause": "Analysis failed due to error",
                "confidence": 0,
                "recommendations": [],
                "error": f"Error in root cause analysis: {str(e)}"
            },
            "raw_analysis": f"Root cause analysis failed: {str(e)}"
        }
        response = json.dumps(error_response, indent=2)
    
    logger.info("Starting JSON parsing of agent response")
    
    try:
        
        root_cause_analysis = response
        # Create the root_cause structure
        context["root_cause"] = response
        
        logger.info("Successfully created root_cause context structure")
        
        # Create a more human-readable response for the message
        human_readable_response = model_direct_invoke(f""" summary the data {response} to the following format:
## Root Cause Analysis Results

**Primary Cause**: 
**Confidence**: 

### Contributing Factors:


### Supporting Evidence:


### Recommended Actions:

I've analyzed all available data and determined the most likely root cause of this incident.
""", "us.anthropic.claude-3-7-sonnet-20250219-v1:0", "us-west-2", 100000)
        
        logger.info("Successfully created human-readable response")
        
    except json.JSONDecodeError as e:
        # Fallback if the response is not valid JSON
        logger.warning(f"JSON parsing failed: {e}. Using fallback response.")
        
        logger.info("Used fallback response due to JSON parsing failure")
    
    # Ensure trace_id is preserved in the output context
    if trace_id:
        context["trace_id"] = trace_id
    
    output_state = {
        "messages": [AIMessage(content=response)],
        "context": context
    }
    
    # Log output state for debugging
    logger.info(f"\n=== ROOT_CAUSE_ANALYSIS_NODE OUTPUT ===")
    logger.info(f"Messages: {output_state['messages'][0].content if output_state['messages'] else 'No messages'}...")
    logger.info(f"Context: {output_state['context']}")
    
    return output_state


def format_list(items: List[str]) -> str:
    """Format a list of items into a readable string"""
    if not items:
        return "- No specific factors identified"
    
    result = ""
    for i, item in enumerate(items, 1):
        result += f"{i}. {item}\n"
    
    return result


def format_evidence(evidence: Dict[str, List[str]]) -> str:
    """Format evidence into a readable string"""
    if not evidence:
        return "- No specific evidence identified"
    
    result = ""
    for category, items in evidence.items():
        if items:
            result += f"**{category.capitalize()}**:\n"
            for item in items:
                result += f"- {item}\n"
            result += "\n"
    
    return result


def format_actions(actions: List[Dict[str, str]]) -> str:
    """Format recommended actions into a readable string"""
    if not actions:
        return "- No specific actions recommended"
    
    result = ""
    for i, action in enumerate(actions, 1):
        action_text = action.get("action", "Unknown action")
        priority = action.get("priority", "Medium")
        impact = action.get("expected_impact", "")
        
        result += f"{i}. **[{priority}]** {action_text}\n"
        if impact:
            result += f"   *Expected impact*: {impact}\n"
    
    return result
