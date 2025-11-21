"""Agent prompt storage in DynamoDB."""
import boto3
from typing import Dict, Any, Optional, List
from datetime import datetime


class PromptStore:
    def __init__(self, table_name: str = 'aiops-agent-prompts'):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
    
    def save_prompt(
        self,
        agent_name: str,
        version: str,
        prompts: Dict[str, str],
        variables: Optional[Dict[str, Any]] = None
    ) -> None:
        """Save agent prompt configuration."""
        item = {
            'agent_name': agent_name,
            'version': version,
            'prompts': prompts,
            'variables': variables or {},
            'updated_at': datetime.utcnow().isoformat()
        }
        self.table.put_item(Item=item)
    
    def get_prompt(self, agent_name: str, version: str) -> Optional[Dict[str, Any]]:
        """Retrieve specific prompt version."""
        response = self.table.get_item(
            Key={'agent_name': agent_name, 'version': version}
        )
        return response.get('Item')
    
    def list_versions(self, agent_name: str) -> List[Dict[str, Any]]:
        """List all versions for an agent."""
        response = self.table.query(
            KeyConditionExpression='agent_name = :name',
            ExpressionAttributeValues={':name': agent_name}
        )
        return response.get('Items', [])
