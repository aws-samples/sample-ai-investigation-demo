"""
LangGraph workflow for AIOps with specialized agents and decision-based routing
"""

from typing import Annotated, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Import centralized logging and trace context
from logging_config import get_workflow_logger
from trace_context import get_current_trace_id

# Import constants
from constants import ContextKeys, AnalysisKeys

# Import all nodes from the nodes package
from nodes import (
    decision_node,
    domain_bot_node,
    resource_collector_node,
    incident_processor_node,
    routing_function,
    alarm_analyzer_node
)

# Import the new root cause analysis node
from nodes.root_cause_analysis_node import root_cause_analysis_node

# Import the new split collector nodes
from nodes.logs_collector_node import logs_collector_node
from nodes.cloudtrail_collector_node import cloudtrail_collector_node

# Import the new split trace finder nodes
from nodes.trace_graph_analyzer_node import trace_graph_analyzer_node
from nodes.trace_details_analyzer_node import trace_details_analyzer_node
from nodes.trace_resource_collector_node import trace_resource_collector_node

# Initialize logger
logger = get_workflow_logger()


class State(TypedDict):
    messages: Annotated[list, add_messages]
    context: Dict[str, Any]


# Initialize the state graph with our State type
graph_builder = StateGraph(State)

# Add nodes to the graph
graph_builder.add_node("alarm_analyzer", alarm_analyzer_node)
graph_builder.add_node("decision", decision_node)
graph_builder.add_node("trace_graph_analyzer", trace_graph_analyzer_node)
graph_builder.add_node("trace_details_analyzer", trace_details_analyzer_node)
graph_builder.add_node("trace_resource_collector", trace_resource_collector_node)
graph_builder.add_node("domain_bot", domain_bot_node)
graph_builder.add_node("resource_collector", resource_collector_node)
graph_builder.add_node("logs_collector", logs_collector_node)
graph_builder.add_node("cloudtrail_collector", cloudtrail_collector_node)
graph_builder.add_node("root_cause_analysis", root_cause_analysis_node)
graph_builder.add_node("incident_processor", incident_processor_node)

# Define the workflow with decision-based routing
graph_builder.add_edge(START, "alarm_analyzer")
graph_builder.add_edge("alarm_analyzer", "decision")

# Add conditional edges based on the routing function
graph_builder.add_conditional_edges(
    "decision",
    routing_function,
    {
        "trace": "trace_graph_analyzer",
        "resource": "domain_bot"
    }
)

# Trace path
graph_builder.add_edge("trace_graph_analyzer", "trace_details_analyzer")
graph_builder.add_edge("trace_details_analyzer", "trace_resource_collector")  # New node after trace details
graph_builder.add_edge("trace_resource_collector", "logs_collector")  # Then collect logs
graph_builder.add_edge("logs_collector", "cloudtrail_collector")  # Then collect CloudTrail
graph_builder.add_edge("cloudtrail_collector", "root_cause_analysis")
graph_builder.add_edge("root_cause_analysis", "incident_processor")

# Standard resource path
graph_builder.add_edge("domain_bot", "resource_collector")
graph_builder.add_edge("resource_collector", "logs_collector")  # First collect logs
graph_builder.add_edge("logs_collector", "cloudtrail_collector")  # Then collect CloudTrail
graph_builder.add_edge("cloudtrail_collector", "root_cause_analysis")
graph_builder.add_edge("root_cause_analysis", "incident_processor")

# All paths end at the incident processor
graph_builder.add_edge("incident_processor", END)

# Compile the graph
graph = graph_builder.compile()


def create_graph():
    """Create and return the compiled graph"""
    return graph


def stream_graph_updates(user_input: str, return_result=False):
    """
    Stream updates from the graph execution
    Enhanced with trace-based logging support
    
    Args:
        user_input (str): The user's input text
        return_result (bool): If True, return the final result instead of just printing
        
    Returns:
        dict: The final state context if return_result is True, otherwise None
    """
    # Get current trace ID for logging context
    current_trace_id = get_current_trace_id()
    
    logger.info(f"Starting AIOps Workflow (Trace: {current_trace_id})")
    if not return_result:
        print("\n--- Starting AIOps Workflow ---")
        if current_trace_id:
            print(f"Trace ID: {current_trace_id}")
    
    # Track which node is currently processing
    current_node = "alarm_analyzer"
    node_names = {
        "alarm_analyzer": "Alarm Analysis System",
        "decision": "Decision System",
        "trace_graph_analyzer": "Trace Graph Analyzer Agent",
        "trace_details_analyzer": "Trace Details Analyzer Agent",
        "trace_resource_collector": "Trace Resource Collector Agent",
        "domain_bot": "Domain Analysis Agent",
        "resource_collector": "Resource Collection Agent",
        "logs_collector": "Logs Collector Agent",
        "cloudtrail_collector": "CloudTrail Collector Agent",
        "root_cause_analysis": "Root Cause Analysis Agent",
        "incident_processor": "Incident Processing Agent"
    }
    
    # Store the path taken for display
    path_taken = ["alarm_analyzer"]
    
    # Store the final result
    final_result = None
    
    try:
        logger.info(f"Processing user input: {user_input[:100]}...")
        
        for event in graph.stream({"messages": [HumanMessage(content=user_input)], "context": {}}):
            # Store the final result
            final_result = event
            
            # Check if this is a new node event
            if "messages" in event and event.get("messages", []):
                message = event["messages"][-1].content
                logger.info(f"Processing event input: {message[:100]}...")
                
                # Check for specific context keys to identify the current node
                if ContextKeys.ALARM_ANALYSIS in message:
                    current_node = "alarm_analyzer"
                elif ContextKeys.INITIAL_DECISION in message:
                    current_node = "decision"
                elif ContextKeys.TRACE_GRAPH_ANALYSIS in message:
                    current_node = "trace_graph_analyzer"
                elif ContextKeys.TRACE_ANALYSIS in message:
                    current_node = "trace_details_analyzer"
                elif ContextKeys.TRACE_RESOURCES in message:
                    current_node = "trace_resource_collector"
                    logger.info(f"🎯 Detected trace_resource_collector node!")
                elif "domain_analysis" in message:
                    current_node = "domain_bot"
                elif "resource_info" in message:
                    current_node = "resource_collector"
                elif "log_analysis" in message:
                    current_node = "logs_collector"
                elif "cloudtrail_analysis" in message:
                    current_node = "cloudtrail_collector"
                elif "root_cause" in message:
                    current_node = "root_cause_analysis"
                elif "incident_info" in message:
                    current_node = "incident_processor"
                if current_node not in path_taken:
                    path_taken.append(current_node)
                
                # Log the node processing
                node_display_name = node_names.get(current_node, 'Agent')
                logger.info(f"Processing node: {node_display_name}")
                
                if not return_result:
                    print(f"\n--- {node_display_name} Response ---")
                
                last_message = event["messages"][-1]
                message_content = ""
                
                if hasattr(last_message, "content"):
                    message_content = last_message.content
                elif isinstance(last_message, dict) and "content" in last_message:
                    message_content = last_message["content"]
                else:
                    message_content = "Message format not recognized"
                
                # Log the message content (truncated for log file)
                logger.info(f"{node_display_name} response: {str(message_content)[:200]}...")
                
                if not return_result:
                    print(message_content)
        
        # Show the path taken at the end
        path_display = " -> ".join([node_names.get(node, node) for node in path_taken])
        logger.info(f"AIOps Workflow Complete. Path taken: {path_display}")
        
        if not return_result:
            print("\n--- AIOps Workflow Complete ---")
            print("Path taken: " + path_display)
            if current_trace_id:
                print(f"Trace ID: {current_trace_id}")
        
        if return_result:
            return final_result.get("context", {})
        
    except Exception as e:
        error_msg = f"Error in workflow: {e}"
        logger.error(error_msg, exc_info=True)
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        if return_result:
            return {"error": str(e)}


if __name__ == "__main__":
    """
    When run directly, create and save the workflow graph visualization
    """
    try:
        print("Creating AIOps workflow graph...")
        
        # Create the graph
        graph = create_graph()
        
        # Generate the graph visualization
        try:
            # Try to get the graph as PNG
            graph_image = graph.get_graph().draw_mermaid_png()
            
            # Save to file
            with open("../graph.png", "wb") as f:
                f.write(graph_image)
            
            print("✅ Graph visualization saved as 'graph.png'")
            
        except Exception as viz_error:
            print(f"⚠️  Could not create PNG visualization: {viz_error}")
            
            # Try alternative: save as Mermaid text
            try:
                mermaid_code = graph.get_graph().draw_mermaid()
                with open("graph.mmd", "w") as f:
                    f.write(mermaid_code)
                print("✅ Graph saved as Mermaid code in 'graph.mmd'")
                print("   You can visualize this at: https://mermaid.live/")
            except Exception as mermaid_error:
                print(f"❌ Could not create Mermaid visualization: {mermaid_error}")
        
        # Print graph information
        print(f"\n📊 Graph Information:")
        print(f"   - Nodes: {len(graph.nodes)}")
        try:
            # Try to get edges information
            graph_def = graph.get_graph()
            edge_count = len(graph_def.edges) if hasattr(graph_def, 'edges') else "Unknown"
            print(f"   - Edges: {edge_count}")
        except:
            print(f"   - Edges: Unable to determine")
        
        try:
            # Try to get entry point
            entry_point = getattr(graph.get_graph(), 'entry_point', 'START')
            print(f"   - Entry point: {entry_point}")
        except:
            print(f"   - Entry point: START (default)")
        
        # Print node list
        print(f"\n🔗 Workflow Nodes:")
        for node_name in graph.nodes:
            print(f"   - {node_name}")
            
    except Exception as e:
        print(f"❌ Error creating graph: {e}")
        import traceback
        traceback.print_exc()
