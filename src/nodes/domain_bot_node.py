"""
Domain bot node for AIOps workflow
"""

from typing import Dict, Any
from langchain_core.messages import AIMessage
import sys
import os
import json

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import get_bedrock_model, create_prompt_template, create_agent_executor, COMMON_TOOLS
from agents.domain_bot_agent import DomainBotAgent

# Import constants
from constants import ContextKeys, AnalysisKeys

# Import centralized logging
from logging_config import get_node_logger

def domain_bot_node(state: Dict[str, Any]):
    """
    Node for domain-specific analysis of the alert.
    """
    # Initialize trace-aware logger
    logger = get_node_logger("domain_bot")
    
    # Log input state for debugging
    logger.info(f"\n=== DOMAIN_BOT_NODE INPUT ===")
    logger.info(f"Messages: {state.get('messages', [])[-1].content if state.get('messages') else 'No messages'}")
    logger.info(f"Context: {json.dumps(state.get('context', {}), indent=2)}")
    
    # Get context from previous nodes
    context = state.get("context", {})
    initial_decision = context.get(ContextKeys.INITIAL_DECISION, {})
    
    logger.info(f"Initial decision available: {'Yes' if initial_decision else 'No'}")
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
    
    # Create a domain bot agent using util.py functions
    domain_bot_instructions = """
    You are a domain expert for AWS services and applications. Your role is to:
    
    1. Analyze alerts and identify the affected AWS resources and services
    2. Provide domain-specific context about the resources and potential issues
    3. Suggest possible causes based on your domain knowledge
    4. Recommend next steps for investigation
    
    You have access to knowledge tools that provide information about AWS alarms and application architecture.
    Use these tools to get detailed information about alarms and application components:
    - Use get_alarm_info to get details about specific alarms
    - Use list_alarms to see all available alarms in the knowledge base
    - Use get_architecture_info to understand the overall application architecture
    - Use get_component_info to get details about specific components
    - Use get_data_flow to understand how data flows through the application
    
    Provide comprehensive analysis based on the available information.
    """
    
    logger.info("Initializing domain bot agent")
    
    # Initialize the Domain Bot Agent
    agent = DomainBotAgent()
    
    # Enhance the prompt with initial decision context
    enhanced_input = message_content
    if initial_decision:
        enhanced_input += "\n\nInitial alert analysis: " + str(initial_decision)
        logger.info("Added initial decision to enhanced input")
    
    logger.info(f"Enhanced input length: {len(enhanced_input)} characters")
    
    try:
        logger.info("Invoking domain bot agent...")
        response = agent.process(enhanced_input)
        logger.info("Domain bot agent completed successfully")
        logger.info(f"Agent response length: {len(response)} characters")
    except Exception as e:
        logger.error(f"Error invoking domain bot agent: {e}", exc_info=True)
        # Create a proper JSON error response instead of plain string
        error_response = {
            "domain_analysis": {
                "affected_resources": [],
                "resource_groups": [],
                "recommendations": [],
                "error": f"Error in domain analysis: {str(e)}"
            },
            "raw_analysis": f"Domain analysis failed: {str(e)}"
        }
        response = json.dumps(error_response, indent=2)
    
    logger.info("Starting domain analysis extraction from response")
    
    # Extract any context from the agent's response
    context["domain_analysis"] = {
        "identified_resources": [],  # In a real implementation, extract these from the response
        "potential_issues": [],      # In a real implementation, extract these from the response
        "raw_analysis": response
    }
    
    logger.info("Updated context with domain analysis information")
    
    output_state = {
        "messages": [AIMessage(content=response)],
        "context": context
    }
    
    # Log output state for debugging
    logger.info(f"\n=== DOMAIN_BOT_NODE OUTPUT ===")
    logger.info(f"Messages: {output_state['messages'][0].content[:200] if output_state['messages'] else 'No messages'}...")
    logger.info(f"Context domain_analysis keys: {list(output_state['context']['domain_analysis'].keys())}")
    logger.info(f"Context: {json.dumps(output_state['context'], indent=2)}")
    
    return output_state
