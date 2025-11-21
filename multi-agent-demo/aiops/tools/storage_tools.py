"""Storage tools for agents to save investigation data."""

import boto3
import json
import os
from datetime import datetime
from strands.tools import tool
from aiops.utils.dynamodb_helper import InvestigationStore
from aiops.utils.context_store import InvestigationContextStore
from aiops.models.enums import MessageType
from typing import Dict, List

store = InvestigationStore()
context_store = InvestigationContextStore()
sqs = boto3.client('sqs')

@tool
def update_confidence(
    investigation_id: str,
    confidence: float,
    hypothesis: str,
    root_cause_candidates: List[str]
) -> str:
    """Update investigation confidence and hypothesis.
    
    Args:
        investigation_id: Investigation ID
        confidence: Confidence score (0.0-1.0)
        hypothesis: Current hypothesis about root cause
        root_cause_candidates: List of potential root causes
        
    Returns:
        Success message
    """
    from aiops.utils.online_logger import log
    try:
        log("tool-update-confidence", f"CALLED: Confidence={confidence:.2f}, Hypothesis={hypothesis[:100]}", investigation_id=investigation_id)
        print(f"🔍 update_confidence CALLED: {confidence:.2f}")
        context_store.update_hypothesis(investigation_id, hypothesis, confidence, root_cause_candidates)
        log("tool-update-confidence", f"SUCCESS: Updated to {confidence:.2f}", investigation_id=investigation_id)
        print(f"✅ Confidence updated to {confidence:.2f}")
        return f"Updated confidence to {confidence:.2f}"
    except Exception as e:
        log("tool-update-confidence", f"ERROR: {e}", level="ERROR", investigation_id=investigation_id)
        print(f"❌ Failed to update confidence: {e}")
        return f"Error updating confidence: {e}"

@tool
def save_investigation_workflow(
    investigation_id: str,
    alarm_summary: Dict,
    tasks: List[Dict]
) -> str:
    """Save investigation workflow to DynamoDB.
    
    Args:
        investigation_id: Unique investigation ID
        alarm_summary: Alarm summary with resource_name, metric, namespace, resource_id, time
        tasks: List of tasks with task_id, agent_type, description, priority
        
    Returns:
        Success message
    """
    # Ensure required fields exist with defaults
    alarm_summary.setdefault('resource_name', 'unknown')
    alarm_summary.setdefault('metric', 'unknown')
    alarm_summary.setdefault('namespace', 'unknown')
    alarm_summary.setdefault('resource_id', 'unknown')
    alarm_summary.setdefault('time', str(int(datetime.utcnow().timestamp())))
    
    store.save_workflow(investigation_id, alarm_summary, tasks)
    return f"Workflow saved for investigation {investigation_id} with {len(tasks)} tasks"

@tool
def add_tasks_to_workflow(
    investigation_id: str,
    tasks: List[Dict],
    reorganize: bool = True
) -> str:
    """Add new tasks to existing workflow and reorganize task IDs.
    
    Args:
        investigation_id: Investigation ID
        tasks: List of new tasks with agent_type, description, priority
        reorganize: Whether to reorganize all task IDs in sequence
        
    Returns:
        Success message
    """
    from aiops.utils.online_logger import log
    log("brain-task-mgmt", f"Adding {len(tasks)} tasks: {[t.get('agent_type') for t in tasks]}", investigation_id=investigation_id)
    added = store.add_tasks(investigation_id, tasks, reorganize)
    log("brain-task-mgmt", f"Added {added} tasks, reorganized={reorganize}", investigation_id=investigation_id)
    return f"Added {added} tasks to investigation {investigation_id}"

@tool
def trigger_investigation(investigation_id: str) -> str:
    """Trigger investigation execution by sending message to SQS queue.
    
    Args:
        investigation_id: Investigation ID to execute
        
    Returns:
        Success message
    """
    from aiops.utils.sqs_helper import send_execution_message
    from aiops.utils.online_logger import log
    
    # Get next pending task ID from DynamoDB
    workflow = store.get_workflow(investigation_id)
    pending_tasks = [t for t in workflow.get('tasks', []) if t.get('status') == 'PENDING']
    next_task = pending_tasks[0].get('task_id', 'none') if pending_tasks else 'none'
    
    success = send_execution_message(investigation_id, next_task)
    
    if success:
        return f"Investigation {investigation_id} triggered for execution (task: {next_task})"
    else:
        return f"Error: Failed to trigger investigation {investigation_id}"

@tool
def store_task_findings(
    investigation_id: str,
    task_id: str,
    summary: str,
    key_findings: List[str],
    evidence: List[str] = None,
    recommendations: List[str] = None
) -> str:
    """Store structured findings from task execution.
    
    Args:
        investigation_id: Investigation ID
        task_id: Task ID
        summary: Brief summary of findings
        key_findings: List of key findings or observations
        evidence: Optional list of supporting evidence
        recommendations: Optional list of recommendations
        
    Returns:
        Success message
    """
    finding_data = {
        "summary": summary,
        "key_findings": key_findings,
        "evidence": evidence or [],
        "recommendations": recommendations or [],
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Get agent type from task
    workflow = store.get_workflow(investigation_id)
    task = next((t for t in workflow.get('tasks', []) if t.get('task_id') == task_id), None)
    agent_type = task.get('agent_type', 'Unknown') if task else 'Unknown'
    
    context_store.update_finding(investigation_id, task_id, agent_type, finding_data)
    return f"Findings stored for task {task_id}"

@tool
def get_investigation_summary(investigation_id: str) -> Dict:
    """Get investigation summary including hypothesis, findings, and confidence.
    
    Args:
        investigation_id: Investigation ID
        
    Returns:
        Dict with investigation summary
    """
    context = context_store.get_context(investigation_id)
    if not context:
        return {"error": f"No context found for investigation {investigation_id}"}
    
    workflow = store.get_workflow(investigation_id)
    
    return {
        "alarm_summary": workflow.get('alarm_summary', {}),
        "current_hypothesis": context.get('current_hypothesis', ''),
        "confidence": context.get('confidence', 0.0),
        "root_cause_candidates": context.get('root_cause_candidates', []),
        "findings": context.get('findings', {}),
        "status": context.get('status', 'UNKNOWN')
    }

@tool
def get_alarm_summary(investigation_id: str) -> Dict:
    """Get alarm summary for an investigation from DynamoDB.
    
    Args:
        investigation_id: Investigation ID
        
    Returns:
        Alarm summary dict with alarm_name, metric_name, namespace, resource_id, threshold, etc.
    """
    workflow = store.get_workflow(investigation_id)
    alarm_summary = workflow.get('alarm_summary', {})
    
    if not alarm_summary:
        return {"error": f"No alarm summary found for investigation {investigation_id}"}
    
    return alarm_summary

@tool
def get_next_task(investigation_id: str) -> Dict:
    """Get the next task to execute from investigation workflow.
    
    Args:
        investigation_id: Investigation ID
        
    Returns:
        Task dict with task_id, agent_type, description, priority
    """
    task = store.get_next_task(investigation_id)
    if task:
        return {
            "task_id": task['task_id'],
            "agent_type": task['agent_type'],
            "description": task['description'],
            "priority": task['priority']
        }
    return {"message": "No pending tasks"}

@tool
def complete_task(
    investigation_id: str,
    task_id: str,
    result: Dict
) -> str:
    """Mark task as completed and save result.
    
    Args:
        investigation_id: Investigation ID
        task_id: Task ID
        result: Task execution result
        
    Returns:
        Success message
    """
    store.complete_task(investigation_id, task_id, result)
    return f"Task {task_id} completed for investigation {investigation_id}"

@tool
def update_context_finding(
    investigation_id: str,
    task_id: str,
    agent_type: str,
    finding_data: Dict
) -> str:
    """Update investigation context with task findings.
    
    Args:
        investigation_id: Investigation ID
        task_id: Task ID
        agent_type: Agent type
        finding_data: Finding data dict
        
    Returns:
        Success message
    """
    context_store.update_finding(investigation_id, task_id, agent_type, finding_data)
    return f"Context updated for {task_id}_{agent_type}"

@tool
def add_context_event(
    investigation_id: str,
    event: str,
    source: str
) -> str:
    """Add event to investigation timeline.
    
    Args:
        investigation_id: Investigation ID
        event: Event description
        source: Event source (agent name)
        
    Returns:
        Success message
    """
    context_store.add_timeline_event(investigation_id, event, source)
    return f"Event added to timeline: {event}"

@tool
def get_investigation_context(investigation_id: str) -> Dict:
    """Get full investigation context.
    
    Args:
        investigation_id: Investigation ID
        
    Returns:
        Full context dict
    """
    context = context_store.get_context(investigation_id)
    if not context:
        return {"error": f"No context found for investigation {investigation_id}"}
    return context

@tool
def store_final_result(
    investigation_id: str,
    root_cause: str,
    findings: List[str],
    confidence: str,
    summary: str
) -> str:
    """Store final investigation result from RootCauseAnalysisAgent.
    
    Args:
        investigation_id: Investigation ID
        root_cause: Root cause statement
        findings: List of top findings
        confidence: Confidence assessment (High|Medium|Low with explanation)
        summary: Investigation summary
        
    Returns:
        Success message
    """
    context_store.store_final_result(investigation_id, root_cause, findings, confidence, summary)
    return f"Final result stored for investigation {investigation_id}"

@tool
def remove_pending_tasks(
    investigation_id: str,
    task_ids: List[str]
) -> str:
    """Remove pending tasks that are no longer needed.
    
    Args:
        investigation_id: Investigation ID
        task_ids: List of task IDs to remove
        
    Returns:
        Success message
    """
    from aiops.utils.online_logger import log
    log("brain-task-mgmt", f"Removing tasks: {task_ids}", investigation_id=investigation_id)
    removed = store.remove_tasks(investigation_id, task_ids)
    log("brain-task-mgmt", f"Removed {removed} tasks, reorganized remaining tasks", investigation_id=investigation_id)
    return f"Removed {removed} pending tasks: {', '.join(task_ids)}"

@tool
def update_task_description(
    investigation_id: str,
    task_id: str,
    new_description: str
) -> str:
    """Update description of a pending task with more specific information.
    
    Args:
        investigation_id: Investigation ID
        task_id: Task ID to update
        new_description: New task description with specific resource names/ARNs
        
    Returns:
        Success message
    """
    from aiops.utils.online_logger import log
    log("brain-task-mgmt", f"Updating task {task_id} description", investigation_id=investigation_id)
    updated = store.update_task_description(investigation_id, task_id, new_description)
    log("brain-task-mgmt", f"Updated task {task_id}: {updated}", investigation_id=investigation_id)
    return f"Updated task {task_id} description"
