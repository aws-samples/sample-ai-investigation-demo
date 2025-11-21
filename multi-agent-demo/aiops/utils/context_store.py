"""Investigation context store for tracking investigation progress."""

import boto3
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal
import os


def convert_floats(obj):
    """Convert float values to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats(i) for i in obj]
    return obj


def convert_decimals(obj):
    """Convert Decimal values to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    return obj


class InvestigationContextStore:
    """Store and update investigation context in DynamoDB (single row per investigation)."""
    
    def __init__(self, table_name: str = None):
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = table_name or os.getenv('CONTEXT_TABLE', 'aiops-investigation-context')
        self.table = self.dynamodb.Table(self.table_name)
    
    def create_context(self, investigation_id: str, alarm_summary: Dict) -> None:
        """Initialize investigation context.
        
        Args:
            investigation_id: Investigation ID
            alarm_summary: Alarm summary dict
        """
        timestamp = datetime.utcnow().isoformat()
        
        self.table.put_item(Item=convert_floats({
            'investigation_id': investigation_id,
            'alarm_summary': alarm_summary,
            'status': 'IN_PROGRESS',
            'confidence': 0.0,
            'current_hypothesis': '',
            'root_cause_candidates': [],
            'findings': {},
            'timeline': [],
            'metrics_snapshot': {},
            'created_at': timestamp,
            'updated_at': timestamp,
            'version': 0
        }))
    
    def update_finding(self, investigation_id: str, task_id: str, agent_type: str, finding_data: Dict) -> None:
        """Update finding for a specific agent task.
        
        Args:
            investigation_id: Investigation ID
            task_id: Task ID (used as prefix)
            agent_type: Agent type
            finding_data: Finding data dict
        """
        timestamp = datetime.utcnow().isoformat()
        key = f"{task_id}_{agent_type}"
        
        finding_data['last_updated'] = timestamp
        
        self.table.update_item(
            Key={'investigation_id': investigation_id},
            UpdateExpression='SET findings.#key = :data, updated_at = :time, version = if_not_exists(version, :zero) + :inc',
            ExpressionAttributeNames={'#key': key},
            ExpressionAttributeValues=convert_floats({
                ':data': finding_data,
                ':time': timestamp,
                ':inc': 1,
                ':zero': 0
            })
        )
    
    def add_timeline_event(self, investigation_id: str, event: str, source: str) -> None:
        """Add event to timeline.
        
        Args:
            investigation_id: Investigation ID
            event: Event description
            source: Event source (agent name)
        """
        timestamp = datetime.utcnow().isoformat()
        
        event_item = {
            'timestamp': timestamp,
            'event': event,
            'source': source
        }
        
        self.table.update_item(
            Key={'investigation_id': investigation_id},
            UpdateExpression='SET timeline = list_append(if_not_exists(timeline, :empty), :event), updated_at = :time, version = if_not_exists(version, :zero) + :inc',
            ExpressionAttributeValues={
                ':event': [event_item],
                ':empty': [],
                ':time': timestamp,
                ':inc': 1,
                ':zero': 0
            }
        )
    
    def update_hypothesis(self, investigation_id: str, hypothesis: str, confidence: float, candidates: List[str]) -> None:
        """Update current hypothesis and root cause candidates.
        
        Args:
            investigation_id: Investigation ID
            hypothesis: Current hypothesis
            confidence: Confidence score (0.0-1.0)
            candidates: List of root cause candidates
        """
        timestamp = datetime.utcnow().isoformat()
        
        self.table.update_item(
            Key={'investigation_id': investigation_id},
            UpdateExpression='SET current_hypothesis = :hyp, confidence = :conf, root_cause_candidates = :candidates, updated_at = :time, version = if_not_exists(version, :zero) + :inc',
            ExpressionAttributeValues=convert_floats({
                ':hyp': hypothesis,
                ':conf': confidence,
                ':candidates': candidates,
                ':time': timestamp,
                ':inc': 1,
                ':zero': 0
            })
        )
    
    def update_status(self, investigation_id: str, status: str) -> None:
        """Update investigation status.
        
        Args:
            investigation_id: Investigation ID
            status: Status (IN_PROGRESS, COMPLETED, FAILED)
        """
        timestamp = datetime.utcnow().isoformat()
        
        self.table.update_item(
            Key={'investigation_id': investigation_id},
            UpdateExpression='SET #status = :status, updated_at = :time, version = if_not_exists(version, :zero) + :inc',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': status,
                ':time': timestamp,
                ':inc': 1,
                ':zero': 0
            }
        )
    
    def store_final_result(self, investigation_id: str, root_cause: str, findings: List[str], confidence: str, summary: str) -> None:
        """Store final investigation result from RootCauseAnalysisAgent.
        
        Args:
            investigation_id: Investigation ID
            root_cause: Root cause statement
            findings: List of top findings
            confidence: Confidence assessment (High|Medium|Low with explanation)
            summary: Investigation summary
        """
        timestamp = datetime.utcnow().isoformat()
        
        result = {
            "root_cause": root_cause,
            "findings": findings,
            "confidence": confidence,
            "summary": summary,
            "timestamp": timestamp
        }
        
        self.table.update_item(
            Key={'investigation_id': investigation_id},
            UpdateExpression='SET final_result = :result, updated_at = :time, version = if_not_exists(version, :zero) + :inc',
            ExpressionAttributeValues=convert_floats({
                ':result': result,
                ':time': timestamp,
                ':inc': 1,
                ':zero': 0
            })
        )
    
    def get_context(self, investigation_id: str) -> Optional[Dict]:
        """Get full investigation context.
        
        Args:
            investigation_id: Investigation ID
            
        Returns:
            Context dict or None
        """
        response = self.table.get_item(Key={'investigation_id': investigation_id})
        item = response.get('Item')
        return convert_decimals(item) if item else None
