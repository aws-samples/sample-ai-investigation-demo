"""Simplified data store for AIOps using DynamoDB"""

import json
import boto3
from datetime import datetime
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError

from ..models.data_models import Investigation
from ..models.enums import InvestigationStatus


class SimpleInvestigationStore:
    """Simple store for investigation data in DynamoDB"""
    
    def __init__(self, table_name: str = "aiops-investigations"):
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
    
    def save_investigation(self, investigation: Investigation) -> bool:
        """Save investigation to DynamoDB"""
        try:
            # Convert investigation to simple dict
            item = {
                'investigation_id': investigation.investigation_id,
                'item_type': 'MAIN',
                'data': self._serialize_investigation(investigation),
                'status': investigation.status.value,
                'created_at': investigation.created_at.isoformat(),
                'updated_at': investigation.updated_at.isoformat(),
                'alarm_name': investigation.alarm_input.alarm_name,
                'alarm_namespace': investigation.alarm_input.namespace
            }
            
            self.table.put_item(Item=item)
            return True
            
        except ClientError as e:
            print(f"Error saving investigation: {e}")
            return False
    
    def get_investigation(self, investigation_id: str) -> Optional[Investigation]:
        """Get investigation from DynamoDB"""
        try:
            response = self.table.get_item(
                Key={
                    'investigation_id': investigation_id,
                    'item_type': 'MAIN'
                }
            )
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            return self._deserialize_investigation(item['data'])
            
        except ClientError as e:
            print(f"Error getting investigation: {e}")
            return None
    
    def list_investigations(self, status: Optional[InvestigationStatus] = None, 
                          limit: int = 50) -> List[Dict[str, Any]]:
        """List investigations with optional status filter"""
        try:
            if status:
                # Query by status using GSI
                response = self.table.query(
                    IndexName='StatusIndex',
                    KeyConditionExpression='#status = :status',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={':status': status.value},
                    ScanIndexForward=False,  # Most recent first
                    Limit=limit
                )
            else:
                # Scan all investigations
                response = self.table.scan(
                    FilterExpression='item_type = :main',
                    ExpressionAttributeValues={':main': 'MAIN'},
                    Limit=limit
                )
            
            investigations = []
            for item in response['Items']:
                investigations.append({
                    'investigation_id': item['investigation_id'],
                    'alarm_name': item['alarm_name'],
                    'alarm_namespace': item['alarm_namespace'],
                    'status': item['status'],
                    'created_at': item['created_at'],
                    'updated_at': item['updated_at']
                })
            
            return investigations
            
        except ClientError as e:
            print(f"Error listing investigations: {e}")
            return []
    
    def update_investigation_status(self, investigation_id: str, 
                                  status: InvestigationStatus) -> bool:
        """Update investigation status"""
        try:
            self.table.update_item(
                Key={
                    'investigation_id': investigation_id,
                    'item_type': 'MAIN'
                },
                UpdateExpression='SET #status = :status, updated_at = :updated',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': status.value,
                    ':updated': datetime.now().isoformat()
                }
            )
            return True
            
        except ClientError as e:
            print(f"Error updating investigation status: {e}")
            return False
    
    def _serialize_investigation(self, investigation: Investigation) -> str:
        """Serialize investigation to JSON string"""
        # Convert to dict with proper serialization
        data = {
            'investigation_id': investigation.investigation_id,
            'alarm_input': {
                'alarm_name': investigation.alarm_input.alarm_name,
                'alarm_description': investigation.alarm_input.alarm_description,
                'metric_name': investigation.alarm_input.metric_name,
                'namespace': investigation.alarm_input.namespace,
                'dimensions': investigation.alarm_input.dimensions,
                'threshold': investigation.alarm_input.threshold,
                'comparison_operator': investigation.alarm_input.comparison_operator,
                'evaluation_periods': investigation.alarm_input.evaluation_periods,
                'datapoints_to_alarm': investigation.alarm_input.datapoints_to_alarm,
                'alarm_state': investigation.alarm_input.alarm_state,
                'state_reason': investigation.alarm_input.state_reason,
                'timestamp': investigation.alarm_input.timestamp.isoformat(),
                'region': investigation.alarm_input.region
            },
            'rounds': [],  # Simplified - store rounds separately if needed
            'current_round': investigation.current_round,
            'status': investigation.status.value,
            'created_at': investigation.created_at.isoformat(),
            'updated_at': investigation.updated_at.isoformat()
        }
        
        return json.dumps(data)
    
    def _deserialize_investigation(self, data_str: str) -> Investigation:
        """Deserialize investigation from JSON string"""
        from ..models.data_models import AlarmInput, Investigation
        
        data = json.loads(data_str)
        
        # Reconstruct alarm input
        alarm_input = AlarmInput(
            alarm_name=data['alarm_input']['alarm_name'],
            alarm_description=data['alarm_input']['alarm_description'],
            metric_name=data['alarm_input']['metric_name'],
            namespace=data['alarm_input']['namespace'],
            dimensions=data['alarm_input']['dimensions'],
            threshold=data['alarm_input']['threshold'],
            comparison_operator=data['alarm_input']['comparison_operator'],
            evaluation_periods=data['alarm_input']['evaluation_periods'],
            datapoints_to_alarm=data['alarm_input']['datapoints_to_alarm'],
            alarm_state=data['alarm_input']['alarm_state'],
            state_reason=data['alarm_input']['state_reason'],
            timestamp=datetime.fromisoformat(data['alarm_input']['timestamp']),
            region=data['alarm_input']['region']
        )
        
        # Reconstruct investigation
        investigation = Investigation(
            investigation_id=data['investigation_id'],
            alarm_input=alarm_input,
            rounds=[],  # Simplified
            current_round=data['current_round'],
            status=InvestigationStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )
        
        return investigation