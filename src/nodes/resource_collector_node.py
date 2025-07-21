"""
Resource collector node for AIOps workflow
"""

from typing import Dict, Any
from langchain_core.messages import AIMessage
import sys
import os
import json

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import get_bedrock_model, create_prompt_template, create_agent_executor, COMMON_TOOLS
from agents.resource_collector_agent import ResourceCollectorAgent

# Import centralized logging
from logging_config import get_node_logger

# Import constants
from constants import ContextKeys, AnalysisKeys

def resource_collector_node(state: Dict[str, Any]):
    """
    Node for collecting resource information related to the incident.
    """
    # Initialize trace-aware logger
    logger = get_node_logger("resource_collector")
    
    # Log input state for debugging
    logger.info(f"\n=== RESOURCE_COLLECTOR_NODE INPUT ===")
    logger.info(f"Messages: {state.get('messages', [])[-1].content if state.get('messages') else 'No messages'}")
    logger.info(f"Context: {json.dumps(state.get('context', {}), indent=2)}")
    
    # Get context from previous nodes
    context = state.get("context", {})
    initial_decision = context.get(ContextKeys.INITIAL_DECISION, {})
    domain_analysis = context.get("domain_analysis", {})
    
    logger.info(f"Initial decision available: {'Yes' if initial_decision else 'No'}")
    logger.info(f"Domain analysis available: {'Yes' if domain_analysis else 'No'}")
    
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
    
    # Create a resource collector agent using util.py functions
    resource_collector_instructions = """
    You are a resource collection expert. Your role is to:
    
    1. Identify AWS resources involved in the incident
    2. Collect detailed information about these resources
    3. Analyze resource configurations, states, and metrics
    4. Identify any resource-related issues that might be causing the problem
    5. Provide a comprehensive resource summary for further analysis
    
    You have access to knowledge tools that provide information about AWS alarms and application architecture.
    Use these tools to understand the resources involved:
    - Use get_alarm_info to get details about specific alarms
    - Use get_architecture_info and get_component_info to understand the application components and their relationships
    - Use get_data_flow to understand how data flows through the application and which resources are involved
    
    Focus on collecting resource data that will help identify the root cause of the incident.
    """
    
    logger.info("Initializing resource collector agent with Bedrock model")
    
    # Initialize the Resource Collector Agent
    agent = ResourceCollectorAgent()
    
    # Build a comprehensive context for the resource collector
    context_summary = []
    
    if initial_decision:
        context_summary.append(f"Initial Analysis: Alert Type: {initial_decision.get('alert_type', 'Unknown')}, Resource Type: {initial_decision.get('resource_type', 'Unknown')}, Severity: {initial_decision.get('severity', 'Medium')}")
        logger.info("Added initial decision to context summary")
    
    if domain_analysis:
        context_summary.append("Domain Analysis: " + str(domain_analysis))
        logger.info("Added domain analysis to context summary")
    
    logger.info(f"Context summary items: {len(context_summary)}")
    
    try:
        logger.info("Invoking resource collector agent...")
        # Invoke the agent
        response = agent.process(f"{message_content}\n\nCollected Information:\n" + "\n".join(context_summary))
        logger.info("Resource collector agent completed successfully")
        logger.info(f"Agent response length: {len(response)} characters")
    except Exception as e:
        logger.error(f"Error invoking resource collector agent: {e}", exc_info=True)
        # Create a proper JSON error response instead of plain string
        error_response = {
            "resource_analysis": {
                "involved_resources": [],
                "resource_states": [],
                "resource_issues": [],
                "error": f"Error in resource collection: {str(e)}"
            },
            "raw_analysis": f"Resource collection failed: {str(e)}"
        }
        response = json.dumps(error_response, indent=2)
    
    logger.info("Starting resource information extraction from response")
    
    # Update context with resource information
    context["resource_info"] = {
        "involved_resources": [],  # In a real implementation, extract these from the response
        "resource_states": [],     # In a real implementation, extract these from the response
        "resource_issues": [],     # In a real implementation, extract these from the response
        "raw_analysis": response
    }
    
    logger.info("Updated context with resource information")
    
    output_state = {
        "messages": [AIMessage(content=response)],
        "context": context
    }
    
    # Log output state for debugging
    logger.info(f"\n=== RESOURCE_COLLECTOR_NODE OUTPUT ===")
    logger.info(f"Messages: {output_state['messages'][0].content[:200] if output_state['messages'] else 'No messages'}...")
    logger.info(f"Context resource_info keys: {list(output_state['context']['resource_info'].keys())}")
    logger.info(f"Context: {json.dumps(output_state['context'], indent=2)}")
    
    return output_state
