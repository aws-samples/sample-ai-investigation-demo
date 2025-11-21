"""
Trace resource collector node for AIOps workflow
Enhanced to provide only relevant resources to the next calling node
"""

import json
import sys
import os
from typing import Dict, Any, List, Tuple
from langchain_core.messages import AIMessage

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logging_config import get_node_logger

# Import constants
from constants import ContextKeys, AnalysisKeys

# Import the agent
from agents.trace_resource_collector_agent import TraceResourceCollectorAgent

# Import AWS context utilities
from aws_context_utils import get_aws_context_from_state, get_default_region, format_aws_context_summary

def trace_resource_collector_node(state: Dict[str, Any], relevance_threshold: float = 0.2):
    """
    Node for collecting detailed resource attributes and metrics.
    Enhanced to filter resources by relevance before passing to the next node.
    
    Input:
    - messages: List of message objects containing previous analysis results
    - context: Dict containing contextual information from previous nodes
      - alarm_analysis: Alarm analysis from alarm analyzer node
      - initial_decision: Decision analysis from decision node
      - trace_analysis: Trace analysis from trace finder node (if trace path)
      - domain_analysis: Domain analysis from domain bot node (if resource path)
      - resource_info: Resource information from resource collector node (if resource path)
    
    Parameters:
    - relevance_threshold: Minimum relevance score (0.0 to 1.0) for resources to be included
    
    Output:
    - messages: Updated with AI response containing resource collection analysis in JSON format
      - resource_collection: structured JSON with filtered resource attributes and metrics
      - relevance_metadata: Information about the filtering process
    - context: Updated context with filtered resource collection information
      - resource_collection: Dict containing detailed resource attributes and metrics
    """
    # Get trace ID from context if available, fallback to current trace
    trace_id = state.get("context", {}).get("trace_id")
    if not trace_id:
        from trace_context import get_current_trace_id
        trace_id = get_current_trace_id()
    
    # Initialize trace-aware logger with explicit trace ID
    logger = get_node_logger("trace_resource_collector", trace_id=trace_id)
    
    # Add prominent logging to detect if node is executing
    logger.info("🚀 TRACE_RESOURCE_COLLECTOR_NODE STARTED")
    logger.info("=" * 60)
    logger.info("🔧 Trace Resource Collector Node is executing!")
    print("🔧 TRACE RESOURCE COLLECTOR NODE EXECUTING!")  # Console output for immediate visibility
    
    logger.info("\n=== TRACE_RESOURCE_COLLECTOR_NODE INPUT ===")
    logger.info(f"Using relevance threshold: {relevance_threshold}")
    
    # Extract message content
    messages = state.get('messages', [])
    message = {}
    
    if messages:
        message_content = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        logger.info(f"Messages: {message_content}")
        
        if message_content:
            try:
                message = json.loads(message_content) if isinstance(message_content, str) else message_content
            except json.JSONDecodeError:
                logger.warning(f"Message content is not valid JSON: {message_content}")
                logger.warning(f"Message content: {message_content}")
                message = {}
        else:
            logger.warning("Message content is empty or None")
    else:
        logger.warning("No messages found in state")
    
    # Extract context information
    context = state.get("context", {})
    logger.info(f"Context: {context}")
    
    # Get all relevant data from the context
    alarm_analysis = context.get(ContextKeys.ALARM_ANALYSIS, {})
    initial_decision = context.get(ContextKeys.INITIAL_DECISION, {})
    trace_graph_analysis = context.get(ContextKeys.TRACE_GRAPH_ANALYSIS, {})
    trace_analysis = message.get(ContextKeys.TRACE_ANALYSIS, {})
    context[ContextKeys.TRACE_ANALYSIS] = trace_analysis
    
    # Extract relevant resources from trace analysis
    relevant_resources = message.get(ContextKeys.TRACE_ANALYSIS, []).get("relevant_resources", {})
    if not relevant_resources and isinstance(trace_analysis, dict):
        relevant_resources = trace_analysis.get("relevant_resources", [])
    
    logger.info(f"Alarm analysis available: {'Yes' if alarm_analysis else 'No'}")
    logger.info(f"Initial decision available: {'Yes' if initial_decision else 'No'}")
    logger.info(f"Trace graph analysis available: {'Yes' if trace_graph_analysis else 'No'}")
    logger.info(f"Trace analysis available: {'Yes' if trace_analysis else 'No'}")
    logger.info(f"Relevant resources count: {len(relevant_resources)}")
    
    # Get AWS context from state
    region, account_id = get_aws_context_from_state(state)
    aws_region = region or get_default_region()
    
    # Log AWS context information
    aws_context_summary = format_aws_context_summary(region, account_id)
    logger.info(f"Using AWS context: {aws_context_summary}")
    logger.info(f"Resource collection will use region: {aws_region}")
    
    # Count context items for logging
    context_items = len(context)
    logger.info(f"Context summary items: {context_items}")
    
    # Create enhanced input for the agent
    enhanced_input = {
        "relevant_resources": relevant_resources,
        "aws_context": {
            "region": aws_region,
            "account_id": account_id
        },
        "alarm_analysis": alarm_analysis,
        # "initial_decision": initial_decision,
        # "trace_analysis": trace_analysis,
        # "trace_graph_analysis": trace_graph_analysis
    }
    
    # Initialize the agent
    agent = TraceResourceCollectorAgent()
    
    try:
        logger.info("Invoking trace resource collector agent...")
        
        # Invoke the agent with the enhanced input
        response = agent.process(enhanced_input)
        
        logger.info("Trace resource collector agent completed successfully")
        logger.info(f"Agent response length: {len(response)} characters")
        
    except Exception as e:
        logger.error(f"Error invoking trace resource collector agent: {e}", exc_info=True)
        # Create a proper JSON error response
        error_response = {
            "resource_collection": {
                "ec2_resources": [],
                "lambda_resources": [],
                "s3_resources": [],
                "rds_resources": [],
                "apigateway_resources": [],
                "dynamodb_resources": [],
                "elb_resources": [],
                "error": f"Error in trace resource collection: {str(e)}"
            },
            "raw_analysis": f"Trace resource collection failed: {str(e)}",
            "recommendations": []
        }
        response = json.dumps(error_response, indent=2)
    
    logger.info("Starting resource collection data structure creation")
    
    # Parse the response to extract resource collection data
    try:
        response_data = json.loads(response)
        
        # Extract resource collection from the response
        resource_collection = response_data.get("resource_collection", {})
        
        # Update context with the resource collection data
        context[ContextKeys.TRACE_RESOURCES] = {
            "resource_collection": resource_collection,
            "raw_analysis": response_data.get("raw_analysis", ""),
            "recommendations": response_data.get("recommendations", []),
            "region_used": response_data.get("region_used", aws_region),
            "total_resources": response_data.get("total_resources", 0)
        }
                
        logger.info("Updated context with actual resource collection data from response")
        logger.info(f"Resource collection contains: {list(resource_collection.keys())}")
        
    except json.JSONDecodeError:
        logger.warning("Could not parse response as JSON, using default structure")
        # Update context with default resource collection data structure
        context[ContextKeys.TRACE_RESOURCES] = {
            "resource_collection": {
                "ec2_resources": [],
                "lambda_resources": [],
                "s3_resources": [],
                "rds_resources": [],
                "apigateway_resources": [],
                "dynamodb_resources": [],
                "elb_resources": [],
                "error": "Failed to parse agent response as JSON"
            },
            "raw_analysis": "Failed to parse agent response",
            "recommendations": []
        }
        logger.info("Updated context with default resource collection data structure")
    
    # Create the output state
    output_state = {
        "messages": [AIMessage(content=response)],
        "context": context
    }
    
    logger.info("\n=== TRACE_RESOURCE_COLLECTOR_NODE OUTPUT ===")
    logger.info(f"Messages: {response[:200]}...")
    logger.info(f"Context keys: {list(context.keys())}")
    
    # Log trace resources specifically for stream callback detection
    if ContextKeys.TRACE_RESOURCES in context:
        trace_resources = context[ContextKeys.TRACE_RESOURCES]
        logger.info(f"✅ TRACE_RESOURCES context key set successfully")
        logger.info(f"Resource collection data keys: {list(trace_resources.get('resource_collection', {}).keys())}")
        logger.info(f"Total resources collected: {trace_resources.get('total_resources', 0)}")
    else:
        logger.warning("❌ TRACE_RESOURCES context key not set - stream callback may not detect this node")
    
    # Add completion logging
    logger.info("🎉 TRACE_RESOURCE_COLLECTOR_NODE COMPLETED SUCCESSFULLY")
    logger.info("=" * 60)
    print("🎉 TRACE RESOURCE COLLECTOR NODE COMPLETED!")  # Console output for immediate visibility
    
    return output_state
