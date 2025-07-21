import streamlit as st
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any
from traceloop.sdk import Traceloop
from dotenv import load_dotenv
load_dotenv()

Traceloop.init()

# Add the current directory to the path so we can import from main.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import functionality from graph.py for streaming
from graph import stream_graph_updates, graph
from langchain_core.messages import HumanMessage

# Import centralized logging and trace context
from logging_config import get_streamlit_logger, list_trace_sessions
from trace_context import start_trace_session, end_trace_session, get_current_trace_id, generate_trace_id

# Import constants
from constants import ContextKeys, AnalysisKeys

# Initialize logger
logger = get_streamlit_logger()

# Define the function to format results as markdown
def format_result_as_markdown(result):
    """Format the result dictionary as markdown for better display"""
    if not result:
        return "No results to display"
    
    markdown = ""
    
    # Handle different result structures
    if "root_cause" in result:
        # Format root cause analysis
        root_cause = result["root_cause"]
        markdown += f"## Root Cause Analysis\n\n"
        
        if "root_cause" in root_cause:
            markdown += f"### Root Cause\n{root_cause['root_cause']}\n\n"
        
        if "analysis" in root_cause:
            markdown += f"### Analysis\n{root_cause['analysis']}\n\n"
        
        if "recommendations" in root_cause:
            markdown += f"### Recommendations\n{root_cause['recommendations']}\n\n"
    
    elif ContextKeys.INITIAL_DECISION in result:
        # Format decision
        decision = result[ContextKeys.INITIAL_DECISION]
        markdown += f"## Decision Analysis\n\n"
        markdown += f"**Alert Type**: {decision.get('alert_type', 'Unknown')}\n\n"
        markdown += f"**Resource Type**: {decision.get('resource_type', 'Unknown')}\n\n"
        markdown += f"**Severity**: {decision.get('severity', 'Unknown')}\n\n"
        markdown += f"**Recommended Path**: {decision.get('recommended_path', 'Unknown')}\n\n"
        
        if "reasoning" in decision:
            markdown += f"### Reasoning\n{decision['reasoning']}\n\n"
    
    elif ContextKeys.ALARM_ANALYSIS in result:
        # Format alarm analysis
        alarm = result[ContextKeys.ALARM_ANALYSIS]
        markdown += f"## Alarm Analysis\n\n"
        
        if "identified_alarm_types" in alarm:
            markdown += f"**Alarm Types**: {', '.join(alarm['identified_alarm_types'])}\n\n"
        
        if "severity" in alarm:
            markdown += f"**Severity**: {alarm['severity']}\n\n"
        
        if "extracted_info" in alarm:
            info = alarm["extracted_info"]
            markdown += f"### Extracted Information\n\n"
            markdown += f"**Alarm Name**: {info.get('alarm_name', 'Unknown')}\n\n"
            markdown += f"**Start Time**: {info.get('alarm_start_time', 'Unknown')}\n\n"
            
            if "related_resources" in info and info["related_resources"]:
                resources = info["related_resources"]
                markdown += f"**Related Resources**:\n"
                for resource in resources:
                    markdown += f"- {resource.get('resource_type', 'Unknown')}: {resource.get('resource_id', 'Unknown')}\n"
                markdown += "\n"
        
        if "possible_causes" in alarm:
            markdown += f"### Possible Causes\n\n"
            for cause in alarm["possible_causes"]:
                markdown += f"- {cause}\n"
            markdown += "\n"
    
    else:
        # Generic formatting for other result types
        markdown += "## Analysis Results\n\n"
        for key, value in result.items():
            if isinstance(value, dict):
                markdown += f"### {key.replace('_', ' ').title()}\n"
                markdown += f"```json\n{json.dumps(value, indent=2)}\n```\n\n"
            else:
                markdown += f"**{key.replace('_', ' ').title()}**: {value}\n\n"
    
    return markdown


def stream_workflow_with_enhanced_ui(user_input: str):
    """
    Simplified workflow streaming with basic status tracking
    """
    # Node names mapping for simple status display (major steps in both paths)
    major_node_names = {
        "alarm_analyzer": "🔍 Alarm Analysis",
        "decision": "🤔 Decision Node", 
        # Trace path
        "trace_graph_analyzer": "📊 Trace Graph Analysis",
        "trace_details_analyzer": "🔍 Trace Details Analysis",
        "trace_resource_collector": "📦 Trace Resource Collector",
        # Resource path  
        "domain_bot": "🏗️ Domain Analysis",
        # Common data collection steps
        "logs_collector": "📋 Logs Collection",
        "cloudtrail_collector": "🛤️ CloudTrail Collection",
        # Common final steps
        "root_cause_analysis": "🎯 Root Cause Analysis",
        "incident_processor": "📝 Incident Report"
    }
    
    # Complete node names mapping for detailed outputs
    all_node_names = {
        "alarm_analyzer": "🔍 Alarm Analysis",
        "decision": "🤔 Decision Node", 
        "trace_graph_analyzer": "📊 Trace Graph Analyzer",
        "trace_details_analyzer": "🔍 Trace Details Analyzer",
        "trace_resource_collector": "📦 Trace Resource Collector",
        "domain_bot": "🏗️ Domain Analysis",
        "resource_collector": "📋 Resource Collector",
        "logs_collector": "📋 Logs Collector",
        "cloudtrail_collector": "🛤️ CloudTrail Collector",
        "root_cause_analysis": "🎯 Root Cause Analysis",
        "incident_processor": "📝 Incident Processor"
    }
    
    # Clear previous outputs and reset progress state
    st.session_state.node_outputs = []
    st.session_state.analysis_complete = False
    st.session_state.final_progress = None
    
    # Create simple status display
    status_container = st.container()
    with status_container:
        st.markdown("#### 🔄 Analysis Status")
        status_text = st.empty()
        workflow_steps = st.empty()
        status_text.info("**Starting Analysis...**")                        
    # Create expandable sections for detailed outputs
    detailed_container = st.container()
    
    try:
        # Track completed major steps for status display
        completed_major_steps = []
        current_major_step = None
        
        # Stream the graph execution
        for event in graph.stream({"messages": [HumanMessage(content=user_input)], "context": {}}, stream_mode="updates"):
            # Extract current node from event
            current_node = None
            logger.info(f"Processing event: {event}")
            
            # Check for any node (for detailed outputs)
            for key in event.keys():
                logger.info(f"Processing event key: {key}")
                if key in all_node_names and key != "messages" and key != "context":
                    current_node = key
                    break
            
            # Update status for major nodes only
            if current_node and current_node in major_node_names and current_node not in completed_major_steps:
                completed_major_steps.append(current_node)
                current_major_step = current_node
                
                # Update status display
                node_display_name = major_node_names.get(current_node, current_node)
                status_text.info(f"**Currently Processing:** {node_display_name}")
                
                # Show workflow progress
                if completed_major_steps:
                    progress_display = " → ".join([major_node_names.get(step, step) for step in completed_major_steps])
                    if current_major_step and current_major_step == completed_major_steps[-1]:
                        progress_display += " (in progress...)"
                    workflow_steps.markdown(f"**Workflow:** {progress_display}")
            
            # Capture ALL node outputs for detailed display
            if current_node in event and event.get(current_node, {}).get("messages", []):
                last_message = event.get(current_node, {}).get("messages", [])[-1]
                # Check if we already captured this node
                already_captured = any(output["node"] == current_node for output in st.session_state.node_outputs)
                
                if not already_captured:
                    message_content = ""
                    
                    if hasattr(last_message, "content"):
                        message_content = last_message.content
                    elif isinstance(last_message, dict) and "content" in last_message:
                        message_content = last_message["content"]
                    else:
                        message_content = str(last_message)
                    
                    # Store detailed output for ALL nodes
                    node_output = {
                        "node": current_node,
                        "display_name": all_node_names.get(current_node, current_node.replace('_', ' ').title()),
                        "content": message_content,
                        "context": event.get(current_node, {}).get("context", {}),
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "processing_time": None
                    }
                    
                    st.session_state.node_outputs.append(node_output)
                    
                    # Show in expandable section if detailed output is enabled (for major nodes only during processing)
                    if st.session_state.show_detailed_output and current_node in major_node_names:
                        node_display_name = major_node_names.get(current_node, current_node)
                        with detailed_container:
                            with st.expander(f"📋 {node_display_name} - Completed at {node_output['timestamp']}", expanded=False):
                                if len(message_content) > 500:
                                    st.markdown("**Summary:**")
                                    st.markdown(message_content[:500] + "...")
                                    if st.button(f"Show Full Output", key=f"full_{current_node}"):
                                        st.markdown("**Full Output:**")
                                        st.markdown(message_content)
                                else:
                                    st.markdown("**Output:**")
                                    st.markdown(message_content)
        
        # Complete the workflow
        status_text.success("✅ **Analysis Completed Successfully!**")
        
        # Final workflow display
        if completed_major_steps:
            final_workflow = " → ".join([major_node_names.get(step, step) for step in completed_major_steps])
            workflow_steps.markdown(f"**Completed Workflow:** {final_workflow}")
        
        # Save final progress state to session
        st.session_state.analysis_complete = True
        st.session_state.final_progress = {
            "completed_steps": completed_major_steps,
            "workflow_path": " → ".join([major_node_names.get(step, step) for step in completed_major_steps]),
            "completion_time": datetime.now().strftime("%H:%M:%S")
        }
        
        # Return the final context
        return event.get("context", {}) if 'event' in locals() else {}
        
    except Exception as e:
        status_text.error(f"❌ **Error:** {str(e)}")
        logger.error(f"Error in workflow streaming: {e}", exc_info=True)
        return {"error": str(e)}

def stream_workflow_with_ui_updates(user_input: str):
    """
    Main workflow streaming function - uses the enhanced UI
    """
    return stream_workflow_with_enhanced_ui(user_input)

# Set page configuration
st.set_page_config(
    page_title="AIOps Investigation Demo",
    page_icon="🔍",
    layout="wide"
)

# Initialize session state for chat history and trace management
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'current_trace_id' not in st.session_state:
    st.session_state.current_trace_id = None

if 'trace_started' not in st.session_state:
    st.session_state.trace_started = False

if 'node_outputs' not in st.session_state:
    st.session_state.node_outputs = []

if 'show_detailed_output' not in st.session_state:
    st.session_state.show_detailed_output = True

if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False

if 'start_analysis' not in st.session_state:
    st.session_state.start_analysis = False

if 'show_debug_info' not in st.session_state:
    st.session_state.show_debug_info = False

# Add title and description
st.title("AIOps Investigation Demo")
st.markdown("""
This application helps you investigate and analyze AWS CloudWatch alarms and trace data.
Enter your alarm description or query below to get started.
""")

# Display current trace ID if available
if st.session_state.current_trace_id:
    st.info(f"🔍 **Latest Analysis Trace:** `{st.session_state.current_trace_id}`\n\nEach new analysis will generate a new trace ID.")

# Display persistent status if analysis was completed
if st.session_state.analysis_complete and st.session_state.final_progress:
    st.markdown("#### 🔄 Analysis Status")
    st.success("✅ **Analysis Completed Successfully!**")
    
    progress_info = st.session_state.final_progress
    st.markdown(f"**Completed Workflow:** {progress_info['workflow_path']}")
    st.markdown(f"**Completed at:** {progress_info['completion_time']}")

# Create sidebar for options
with st.sidebar:
    st.header("Options")
    
    # Trace Management Section
    st.subheader("🔍 Trace Management")
    
    # Show current trace ID if available
    if st.session_state.current_trace_id:
        st.info(f"**Current Trace:** `{st.session_state.current_trace_id[:20]}...`")
    else:
        st.info("**No active trace** - Click 'Analyze' to start")
    
    if st.button("Clear Trace", help="Clear current trace and reset session"):
        if st.session_state.current_trace_id:
            logger.info(f"Clearing trace: {st.session_state.current_trace_id}")
        st.session_state.current_trace_id = None
        st.session_state.trace_started = False
        st.session_state.node_outputs = []  # Clear outputs
        st.success("Trace cleared")
        st.rerun()
    
    # Show recent traces
    if st.checkbox("Show Recent Traces"):
        try:
            recent_traces = list_trace_sessions(days_back=3)
            if recent_traces:
                st.write("**Recent Traces:**")
                for trace in recent_traces[:5]:  # Show last 5
                    trace_id = trace['trace_id']
                    start_time = trace.get('start_time', 'Unknown')
                    status = trace.get('status', 'unknown')
                    
                    # Format display
                    display_id = trace_id.replace('trace-', '')[:16] + '...'
                    if start_time != 'Unknown':
                        try:
                            dt = datetime.fromisoformat(start_time)
                            time_str = dt.strftime('%m/%d %H:%M')
                        except:
                            time_str = start_time[:16]
                    else:
                        time_str = 'Unknown'
                    
                    st.text(f"{display_id} | {time_str} | {status}")
            else:
                st.write("No recent traces found")
        except Exception as e:
            st.write(f"Error loading traces: {e}")
    
    st.divider()
    
    # Display Options
    st.subheader("📊 Display Options")
    st.session_state.show_detailed_output = st.checkbox(
        "Show Detailed Node Outputs", 
        value=st.session_state.show_detailed_output,
        help="Show output from each node in the workflow"
    )
    
    # Debug info
    st.session_state.show_debug_info = st.checkbox(
        "Show Debug Info", 
        value=st.session_state.show_debug_info,
        help="Show debugging information about the analysis"
    )
    
    if st.session_state.show_debug_info:
        st.write(f"**Node outputs count:** {len(st.session_state.node_outputs)}")
        st.write(f"**Show detailed output:** {st.session_state.show_detailed_output}")
        st.write(f"**Analysis complete:** {st.session_state.analysis_complete}")
        st.write(f"**Current trace ID:** {st.session_state.current_trace_id}")
        if st.session_state.node_outputs:
            st.write("**Node output keys:**")
            for i, output in enumerate(st.session_state.node_outputs):
                st.write(f"  {i+1}. {output.get('display_name', 'Unknown')} - Content length: {len(output.get('content', ''))}")
        else:
            st.write("**No node outputs captured yet**")
    st.divider()
    
    # Add sample inputs dropdown
    st.subheader("📋 Sample Alarms")
    sample_option = st.selectbox(
        "Choose a sample alarm",
        ["None", "API Gateway Error Rate", "RDS Connection Failures", "High CPU Utilization"]
    )
    
    # Sample alarm texts
    sample_alarms = {
        "API Gateway Error Rate": """
ALARM: "API Gateway Error Rate High" in US East (N. Virginia)
Threshold Crossed: 3 datapoints [5.2 (10/06/25 01:50:00), 7.8 (10/06/25 01:55:00), 12.3 (10/06/25 02:00:00)] was greater than the threshold (1.0).
Alarm Details:
- Name: API-Gateway-Error-Rate-High
- Description: API Gateway endpoint /api/orders is experiencing high error rates
- State Change: OK -> ALARM
- Reason: Threshold Crossed
- Timestamp: 2025-06-10T02:00:00Z
- AWS Account: 123456789012
- Region: us-east-1
- Dimensions: ApiName=OrdersAPI, Stage=prod, Resource=/api/orders, Method=POST
        """,
        "RDS Connection Failures": """
ALARM: "Database Connection Failures" in US East (N. Virginia)
Threshold Crossed: 5 datapoints [10.5 (10/06/25 01:45:00), 12.3 (10/06/25 01:50:00), 15.7 (10/06/25 01:55:00), 18.2 (10/06/25 02:00:00), 20.1 (10/06/25 02:05:00)] was greater than the threshold (5.0).
Alarm Details:
- Name: RDS-Connection-Failures
- Description: Production database is experiencing connection failures
- State Change: OK -> ALARM
- Reason: Threshold Crossed
- Timestamp: 2025-06-10T02:05:00Z
- AWS Account: 123456789012
- Region: us-east-1
- Dimensions: DBInstanceIdentifier=prod-postgres-db
        """,
        "High CPU Utilization": """
ALARM: "High CPU Utilization" in US West (Oregon)
Threshold Crossed: 1 datapoint [90.25 (22/05/25 06:15:00)] was greater than the threshold (80.0).
Alarm Details:
- Name: High-CPU-Alarm
- Description: EC2 instance i-0515355a75c579ece has high CPU utilization
- State Change: OK -> ALARM
- Reason: Threshold Crossed
- Timestamp: 2025-05-22T06:15:00Z
- AWS Account: 613477150601
- Region: ap-southeast-1
- Dimensions: InstanceId=i-0515355a75c579ece
        """
    }
    
    # Add a button to clear chat history
    if st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.session_state.node_outputs = []
        logger.info("Chat history cleared by user")
        st.success("Chat history cleared!")
    
    # Add information about the app
    st.divider()
    st.subheader("ℹ️ About")
    st.markdown("""
    This application uses AI to analyze CloudWatch alarms and trace data to help identify root causes of issues in AWS environments.
    
    **Trace Features:**
    - Each analysis gets a unique trace ID
    - All logs are organized by trace
    - View recent trace sessions
    - Start new traces for fresh analysis
    
    **Detailed Output:**
    - See each node's analysis step-by-step
    - Track workflow progress in real-time
    - Complete visibility into AI reasoning
    """)

# Main chat interface
# st.header("Investigation Chat")

# Display chat history
# for message in st.session_state.chat_history:
#     if message["role"] == "user":
#         st.markdown(f"**You**: {message['content']}")
#     else:
#         st.markdown(f"**AI**: {message['content']}")

# Display detailed node outputs if enabled and available
if st.session_state.show_detailed_output and st.session_state.node_outputs:
    st.header("🔍 Detailed Workflow Analysis")
    
    # Debug info
    st.write(f"**Debug:** Found {len(st.session_state.node_outputs)} node outputs")
    
    # Create tabs for each node
    if len(st.session_state.node_outputs) > 1:
        tab_names = [output["display_name"] for output in st.session_state.node_outputs]
        tabs = st.tabs(tab_names)
        
        for i, (tab, output) in enumerate(zip(tabs, st.session_state.node_outputs)):
            with tab:
                st.markdown(f"### {output['display_name']}")
                st.markdown(f"**Timestamp:** {output.get('timestamp', 'Unknown')}")
                
                # Show content
                if output.get("content"):
                    st.markdown("**Output:**")
                    # if output['display_name'].startswith("🎯"):
                    #     st.markdown(output["content"])
                    # else:
                    st.json(output["content"])
                else:
                    st.warning("No content available for this node")
                
                # Show context information if available
                if output.get("context") and st.checkbox(f"Show Context Data", key=f"context_{i}"):
                    st.json(output["context"])
    else:
        # Single node output
        if st.session_state.node_outputs:
            output = st.session_state.node_outputs[-1]
            st.markdown(f"### {output['display_name']}")
            st.markdown(f"**Timestamp:** {output.get('timestamp', 'Unknown')}")
            
            if output.get("content"):
                st.markdown("**Output:**")
                st.markdown(output["content"])
            else:
                st.warning("No content available for this node")
            
            if output.get("context") and st.checkbox("Show Context Data"):
                st.json(output["context"])
elif st.session_state.show_detailed_output:
    st.info("🔍 **Detailed outputs will appear here after running an analysis**")
elif st.session_state.node_outputs:
    st.info("📊 **Enable 'Show Detailed Node Outputs' in the sidebar to see detailed analysis**")
        
# Input area
user_input = st.text_area("Enter your alarm description or query:", height=150)

# Handle sample selection
if sample_option != "None":
    user_input = sample_alarms[sample_option]
    st.session_state.selected_sample = sample_option

# Process button
if st.button("Analyze"):
    if user_input:
        # Clear previous analysis state immediately when new analysis starts
        st.session_state.analysis_complete = False
        st.session_state.final_progress = None
        st.session_state.node_outputs = []  # Clear previous outputs
        
        # Set up for analysis
        st.session_state.start_analysis = True
        st.session_state.analysis_input = user_input
        
        # Always generate a new trace ID for each analysis
        new_trace_id = generate_trace_id()
        st.session_state.current_trace_id = new_trace_id
        st.session_state.trace_started = False
        logger.info(f"Generated new trace ID for analysis: {new_trace_id}")
        
        # Start the new trace session
        start_trace_session(st.session_state.current_trace_id)
        st.session_state.trace_started = True
        logger.info(f"Started trace session: {st.session_state.current_trace_id}")
        
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Rerun to clear the old progress display and start fresh
        st.rerun()

# Check if we should start analysis (after rerun)
if st.session_state.start_analysis and st.session_state.analysis_input:
    user_input_to_process = st.session_state.analysis_input
    
    # Reset the flag
    st.session_state.start_analysis = False
    st.session_state.analysis_input = ""
    
    # Show a spinner while processing
    with st.spinner("Analyzing..."):
        try:
            logger.info(f"Processing input with trace ID: {st.session_state.current_trace_id}")
            logger.info(f"Input: {user_input_to_process[:100]}...")
            
            # Use the streaming workflow function
            result = stream_workflow_with_ui_updates(user_input_to_process)
            
            # Create a summary response from the final result
            if isinstance(result, dict) and "error" not in result:
                # Format the final result as a summary
                summary_parts = []
                
                if "root_cause" in result:
                    root_cause = result["root_cause"]
                    summary_parts.append(f"**Root Cause**: {root_cause.get('identified_cause', 'Unknown')}")
                    summary_parts.append(f"**Confidence**: {int(root_cause.get('confidence_score', 0.0) * 100)}%")
                
                if "incident_info" in result:
                    summary_parts.append("**Incident Report**: Generated successfully")
                
                # Add workflow path information
                if st.session_state.node_outputs:
                    path_taken = " → ".join([output["display_name"] for output in st.session_state.node_outputs])
                    summary_parts.append(f"**Workflow Path**: {path_taken}")
                
                response = "\n\n".join(summary_parts) if summary_parts else "Analysis completed successfully"
            else:
                response = f"Analysis completed with {len(st.session_state.node_outputs)} processing steps"
            
            # Add AI response to chat history
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            
            logger.info("Analysis completed successfully")
            
            # Show trace completion info with new trace ID
            st.success(f"✅ Analysis completed! New Trace ID: `{st.session_state.current_trace_id}`")
            
        except Exception as e:
            error_message = f"Error processing input: {str(e)}"
            logger.error(error_message, exc_info=True)
            
            # Add error message to chat history
            st.session_state.chat_history.append({"role": "assistant", "content": f"⚠️ {error_message}"})
    
    # Rerun to update the UI with the new messages and final progress
    st.rerun()

# Run the Streamlit app
if __name__ == "__main__":
    logger.info("Streamlit app started")
    
    # Note: Trace ID is now generated automatically when "Analyze" is clicked
