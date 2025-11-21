#!/usr/bin/env python3
"""Streamlit app for AIOps investigation monitoring and triggering."""

import streamlit as st
import boto3
import json
import time
from datetime import datetime, timedelta
import os

# AWS clients
bedrock_agentcore = boto3.client('bedrock-agentcore')
dynamodb = boto3.resource('dynamodb')
logs_client = boto3.client('logs')

# Configuration from environment
AGENT_RUNTIME_ARN = os.getenv('AGENT_RUNTIME_ARN', '')
INVESTIGATIONS_TABLE = os.getenv('INVESTIGATIONS_TABLE', 'aiops-investigations')
CONTEXT_TABLE = os.getenv('CONTEXT_TABLE', 'aiops-investigation-context')
LOG_GROUP = os.getenv('AGENTCORE_LOG_GROUP', '/aws/bedrock-agentcore/runtime')

st.set_page_config(page_title="AIOps Monitor", layout="wide")
st.title("🔍 AIOps Investigation Monitor")

# Initialize session state
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False

# Sidebar configuration
with st.sidebar:
    st.header("Configuration")
    runtime_arn = st.text_input("Agent Runtime ARN", value=AGENT_RUNTIME_ARN)
    auto_refresh = st.checkbox("Auto-refresh (5s)", value=st.session_state.auto_refresh, key='auto_refresh')
    st.divider()
    st.header("Tables")
    st.text(f"Workflow: {INVESTIGATIONS_TABLE}")
    st.text(f"Context: {CONTEXT_TABLE}")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["🚀 Trigger", "📊 Investigations", "🔄 Progress Monitor", "📝 Logs"])

# Tab 1: Trigger Investigation
with tab1:
    st.header("Trigger New Investigation")
    
    alarm_input = st.text_area(
        "Alarm Content (multi-line)",
        height=200,
        placeholder="Paste CloudWatch alarm JSON or text here..."
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🚀 Trigger", type="primary"):
            if not alarm_input:
                st.error("Please provide alarm content")
            elif not runtime_arn:
                st.error("Please configure Agent Runtime ARN")
            else:
                with st.spinner("Triggering investigation..."):
                    try:
                        payload = json.dumps({"alarm": alarm_input})
                        
                        response = bedrock_agentcore.invoke_agent_runtime(
                            agentRuntimeArn=runtime_arn,
                            qualifier='DEFAULT',
                            payload=payload.encode('utf-8')
                        )
                        
                        # Response is dict with StreamingBody
                        result = json.loads(response['response'].read())
                        print(result)
                        
                        st.success(f"✅ Investigation triggered: {result.get('investigation_id', 'N/A')}")
                        st.json(result)
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

# Tab 2: Investigation Status
with tab2:
    st.header("Investigation Status")
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Get investigations
    try:
        workflow_table = dynamodb.Table(INVESTIGATIONS_TABLE)
        context_table = dynamodb.Table(CONTEXT_TABLE)
        
        # Scan workflow table for metadata
        investigations = []
        response = workflow_table.scan(
            FilterExpression='item_type = :type',
            ExpressionAttributeValues={':type': 'METADATA'}
        )
        investigations.extend(response.get('Items', []))
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = workflow_table.scan(
                FilterExpression='item_type = :type',
                ExpressionAttributeValues={':type': 'METADATA'},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            investigations.extend(response.get('Items', []))
        
        if investigations:
            for inv in sorted(investigations, key=lambda x: x.get('created_at', ''), reverse=True):
                inv_id = inv['investigation_id']
                
                with st.expander(f"📋 {inv_id} - {inv.get('status', 'UNKNOWN')}", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Workflow")
                        st.json({
                            "status": inv.get('status'),
                            "created_at": inv.get('created_at'),
                            "alarm_summary": inv.get('alarm_summary', {}),
                            "execution_plan": inv.get('execution_plan', {})
                        })
                    
                    with col2:
                        st.subheader("Context")
                        try:
                            ctx_response = context_table.get_item(Key={'investigation_id': inv_id})
                            if 'Item' in ctx_response:
                                ctx = ctx_response['Item']
                                st.json({
                                    "confidence": ctx.get('confidence', 0),
                                    "hypothesis": ctx.get('current_hypothesis', ''),
                                    "findings": ctx.get('findings', {}),
                                    "timeline": ctx.get('timeline', [])
                                })
                            else:
                                st.info("No context found")
                        except Exception as e:
                            st.error(f"Error loading context: {e}")
        else:
            st.info("No investigations found")
            
    except Exception as e:
        st.error(f"Error loading investigations: {str(e)}")

# Tab 3: Progress Monitor
with tab3:
    st.header("Real-Time Progress Monitor")
    
    if auto_refresh:
        st.info("🔄 Auto-refresh enabled - updates every 5 seconds")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        investigation_id = st.text_input("Investigation ID", placeholder="Enter investigation ID to monitor")
    with col2:
        st.write("")
        st.write("")
        monitor_refresh = st.button("🔄 Refresh Now")
    
    if investigation_id:
        try:
            workflow_table = dynamodb.Table(INVESTIGATIONS_TABLE)
            context_table = dynamodb.Table(CONTEXT_TABLE)
            logs_table = dynamodb.Table(os.getenv('LOGS_TABLE', 'aiops-logs'))
            
            # Get workflow tasks
            workflow_response = workflow_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('investigation_id').eq(investigation_id)
            )
            workflow_items = workflow_response.get('Items', [])
            
            # Get context
            context_response = context_table.get_item(Key={'investigation_id': investigation_id})
            context = context_response.get('Item', {})
            
            # Get logs
            logs_response = logs_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('component').eq(investigation_id),
                ScanIndexForward=False,
                Limit=50
            )
            logs = logs_response.get('Items', [])
            
            # Display progress
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Status", context.get('status', 'UNKNOWN'))
            with col2:
                confidence = float(context.get('confidence', 0)) * 100
                st.metric("Confidence", f"{confidence:.0f}%")
            with col3:
                completed = len([i for i in workflow_items if i.get('item_type', '').startswith('RESULT#')])
                total = len([i for i in workflow_items if i.get('item_type', '').startswith('TASK#')])
                st.metric("Progress", f"{completed}/{total} tasks")
            
            st.divider()
            
            # Steps section
            st.subheader("📋 Investigation Steps")
            tasks = [i for i in workflow_items if i.get('item_type', '').startswith('TASK#')]
            results = {i['item_type'].replace('RESULT#', 'TASK#'): i for i in workflow_items if i.get('item_type', '').startswith('RESULT#')}
            
            def get_priority(task):
                p = task.get('priority', 999)
                if isinstance(p, str):
                    return {'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}.get(p.upper(), 999)
                return int(p)
            
            for task in sorted(tasks, key=get_priority):
                task_id = task.get('task_id', 'unknown')
                agent_type = task.get('agent_type', 'Unknown')
                description = task.get('description', 'No description')
                
                result = results.get(task['item_type'])
                status = "✅ Completed" if result else "⏳ Pending"
                
                with st.expander(f"{status} - {agent_type} ({task_id})", expanded=not result):
                    st.write(f"**Description:** {description}")
                    if result:
                        st.write("**Output:**")
                        st.json(result.get('result', {}))
            
            st.divider()
            
            # Findings section
            st.subheader("🔍 Findings")
            findings = context.get('findings', {})
            if findings:
                for key, value in findings.items():
                    with st.expander(f"Finding: {key}"):
                        st.json(value)
            else:
                st.info("No findings yet")
            
            st.divider()
            
            # Timeline section
            st.subheader("⏱️ Timeline")
            timeline = context.get('timeline', [])
            if timeline:
                for event in reversed(timeline[-10:]):  # Show last 10 events
                    st.text(f"[{event.get('timestamp', 'N/A')}] {event.get('event', 'N/A')}")
            else:
                st.info("No timeline events")
            
            st.divider()
            
            # Logs section
            st.subheader("📝 Investigation Logs")
            if logs:
                for log in logs[:20]:  # Show last 20 logs
                    level = log.get('level', 'INFO')
                    color = {"ERROR": "🔴", "WARNING": "🟡", "INFO": "🔵"}.get(level, "⚪")
                    st.text(f"{color} [{log.get('time', 'N/A')}] {log.get('message', 'N/A')}")
            else:
                st.info("No logs found")
                
        except Exception as e:
            st.error(f"Error loading progress: {str(e)}")
    else:
        st.info("Enter an investigation ID to monitor progress")

# Tab 4: CloudWatch Logs
with tab4:
    st.header("Application Logs")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        log_investigation_id = st.text_input("Investigation ID (optional)", placeholder="Leave empty for all logs")
    with col2:
        st.write("")
        st.write("")
        if st.button("📝 Fetch Logs"):
            st.rerun()
    
    try:
        logs_table = dynamodb.Table(os.getenv('LOGS_TABLE', 'aiops-logs'))
        
        if log_investigation_id:
            # Query logs for specific investigation
            response = logs_table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('component').eq(log_investigation_id),
                ScanIndexForward=False,
                Limit=100
            )
        else:
            # Scan for recent logs
            response = logs_table.scan(Limit=100)
            items = response.get('Items', [])
            # Sort by time descending
            items.sort(key=lambda x: x.get('time', ''), reverse=True)
            response['Items'] = items
        
        logs = response.get('Items', [])
        
        if logs:
            st.info(f"Found {len(logs)} log entries")
            for log in logs:
                level = log.get('level', 'INFO')
                color = {"ERROR": "🔴", "WARNING": "🟡", "INFO": "🔵"}.get(level, "⚪")
                component = log.get('component', 'unknown')
                log_time = log.get('time', 'N/A')
                message = log.get('log', 'N/A')  # Field is 'log' not 'message'
                st.text(f"{color} [{log_time}] [{component}] {message}")
        else:
            st.info("No logs found")
            
    except Exception as e:
        st.error(f"Error fetching logs: {str(e)}")

# Auto-refresh
if auto_refresh:
    time.sleep(5)
    st.rerun()
