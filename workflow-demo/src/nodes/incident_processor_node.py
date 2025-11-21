"""
Incident processor node for AIOps workflow
"""

from typing import Dict, Any
from langchain_core.messages import AIMessage
import sys
import os
import json

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import get_bedrock_model, create_prompt_template, create_agent_executor, COMMON_TOOLS
from agents.incident_processor_agent import IncidentProcessorAgent

# Import centralized logging
from logging_config import get_node_logger

# Import constants
from constants import ContextKeys, AnalysisKeys

def incident_processor_node(state: Dict[str, Any]):
    """
    Node for processing incident information and providing final recommendations.
    
    Input:
    - messages: List of message objects containing analysis results from previous nodes
    - context: Dict containing contextual information from all previous nodes
      - initial_decision: Decision analysis from decision node
      - trace_analysis: Trace analysis from trace finder node (if trace path)
      - domain_analysis: Domain analysis from domain bot node (if resource path)
      - resource_info: Resource information from resource collector node (if resource path)
      - logs_data: Logs data from logs collector node
      - cloudtrail_data: CloudTrail data from CloudTrail collector node
      - alarm_analysis: Alarm analysis from alarm analyzer node
    
    Output:
    - messages: Updated with AI response containing final incident report
    - context: Updated context with incident processing information
      - incident_info: Dict containing root cause, resolution, and prevention measures
    """
    # Get trace ID from context if available, fallback to current trace
    trace_id = state.get("context", {}).get("trace_id")
    if not trace_id:
        from trace_context import get_current_trace_id
        trace_id = get_current_trace_id()
    
    # Initialize trace-aware logger with explicit trace ID
    logger = get_node_logger("incident_processor", trace_id=trace_id)
    
    # Log input state for debugging
    logger.info(f"\n=== INCIDENT_PROCESSOR_NODE INPUT ===")
    logger.info(f"Messages: {state.get('messages', [])[-1].content if state.get('messages') else 'No messages'}")
    logger.info(f"Context: {json.dumps(state.get('context', {}), indent=2)}")
    
    # Get context from previous nodes
    context = state.get("context", {})
    initial_decision = context.get(ContextKeys.INITIAL_DECISION, {})
    trace_analysis = context.get(ContextKeys.TRACE_ANALYSIS, {})
    domain_analysis = context.get("domain_analysis", {})
    resource_info = context.get("resource_info", {})
    logs_data = context.get("logs_data", {})
    cloudtrail_data = context.get("cloudtrail_data", {})
    alarm_analysis = context.get(ContextKeys.ALARM_ANALYSIS, {})
    
    logger.info(f"Initial decision available: {'Yes' if initial_decision else 'No'}")
    logger.info(f"Trace analysis available: {'Yes' if trace_analysis else 'No'}")
    logger.info(f"Domain analysis available: {'Yes' if domain_analysis else 'No'}")
    logger.info(f"Resource info available: {'Yes' if resource_info else 'No'}")
    logger.info(f"Logs data available: {'Yes' if logs_data else 'No'}")
    logger.info(f"CloudTrail data available: {'Yes' if cloudtrail_data else 'No'}")
    logger.info(f"Alarm analysis available: {'Yes' if alarm_analysis else 'No'}")
    
    # Count available data sources
    available_sources = sum([
        bool(initial_decision), bool(trace_analysis), bool(domain_analysis),
        bool(resource_info), bool(logs_data), bool(cloudtrail_data), bool(alarm_analysis)
    ])
    logger.info(f"Total data sources available: {available_sources}/8")
    
    if initial_decision:
        logger.info(f"Alert type: {initial_decision.get('alert_type', 'Unknown')}, Severity: {initial_decision.get('severity', 'Medium')}")
    
    # Extract the content from the message object
    message_content = ""
    if state["messages"]:
        last_message = state["messages"][-1]
        if hasattr(last_message, "content"):
            message_content = last_message.content
        elif isinstance(last_message, dict) and "content" in last_message:
            message_content = last_message["content"]
    
    logger.info(f"Processing message content length: {len(message_content)} characters")
    
    logger.info("Initializing incident processor agent with Bedrock model")
    
    # Initialize the Incident Processor Agent
    agent = IncidentProcessorAgent()
    
    # Build a comprehensive context for the incident processor
    context_summary = []
    
    if alarm_analysis:
        context_summary.append("Alarm Analysis: " + str(alarm_analysis.get('raw_analysis', 'No alarm analysis available')))
        logger.info("Added alarm analysis to context summary")
    
    if initial_decision:
        context_summary.append(f"Initial Analysis: Alert Type: {initial_decision.get('alert_type', 'Unknown')}, Resource Type: {initial_decision.get('resource_type', 'Unknown')}, Severity: {initial_decision.get('severity', 'Medium')}")
        logger.info("Added initial decision to context summary")
    
    if trace_analysis:
        context_summary.append("Trace Analysis: " + str(trace_analysis))
        logger.info("Added trace analysis to context summary")
    
    if domain_analysis:
        context_summary.append("Domain Analysis: " + str(domain_analysis))
        logger.info("Added domain analysis to context summary")
    
    if resource_info:
        context_summary.append("Resource Information: " + str(resource_info))
        logger.info("Added resource information to context summary")
    
    if logs_data:
        context_summary.append("Logs Data: " + str(logs_data))
        logger.info("Added logs data to context summary")
    
    if cloudtrail_data:
        context_summary.append("CloudTrail Data: " + str(cloudtrail_data))
        logger.info("Added CloudTrail data to context summary")
    
    logger.info(f"Context summary items: {len(context_summary)}")
    
    try:
        logger.info("Invoking incident processor agent...")
        
        # Invoke the agent
        response = agent.process(f"{message_content}\n\nCollected Information:\n" + "\n".join(context_summary))
        
        logger.info("Incident processor agent completed successfully")
        logger.info(f"Agent response length: {len(response)} characters")
        
    except Exception as e:
        logger.error(f"Error invoking incident processor agent: {e}", exc_info=True)
        # Create a proper JSON error response instead of plain string
        error_response = {
            "incident_analysis": {
                "summary": "Incident processing failed",
                "severity": "Unknown",
                "recommendations": [],
                "error": f"Error in incident processing: {str(e)}"
            },
            "raw_analysis": f"Incident processing failed: {str(e)}"
        }
        response = json.dumps(error_response, indent=2)
    
    logger.info("Starting incident information extraction from response")
    
    # Update context with incident information
    # context["incident_info"] = {
    #     "root_cause": "",  # In a real implementation, extract these from the response
    #     "resolution": "",  # In a real implementation, extract these from the response
    #     "prevention": "",  # In a real implementation, extract these from the response
    # }
    
    logger.info("Updated context with incident information structure")
    
    # Ensure trace_id is preserved in the output context
    if trace_id:
        context["trace_id"] = trace_id
    
    output_state = {
        "messages": [AIMessage(content=response)],
        "context": context
    }
    
    # Log output state for debugging
    logger.info(f"\n=== INCIDENT_PROCESSOR_NODE OUTPUT ===")
    logger.info(f"Messages: {output_state['messages'][0].content[:200] if output_state['messages'] else 'No messages'}...")
    logger.info(f"Final incident report generated with {available_sources} data sources")
    
    return output_state
