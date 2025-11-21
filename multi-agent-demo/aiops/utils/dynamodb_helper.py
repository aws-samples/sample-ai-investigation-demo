"""DynamoDB helper for storing investigations and workflows."""

import boto3
from datetime import datetime
from typing import Dict, List, Optional
import os
from aiops.utils.online_logger import log

class InvestigationStore:
    """Store and retrieve investigation workflows in DynamoDB."""
    
    def __init__(self, table_name: str = None):
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = table_name or os.getenv('INVESTIGATIONS_TABLE', 'aiops-investigations')
        self.table = self.dynamodb.Table(self.table_name)
    
    def save_workflow(self, investigation_id: str, alarm_summary: Dict, tasks: List[Dict]) -> None:
        """Save investigation workflow to DynamoDB.
        
        Args:
            investigation_id: Unique investigation ID
            alarm_summary: Alarm summary dict
            tasks: List of task dicts
        """
        timestamp = datetime.utcnow().isoformat()
        task_ids = [task['task_id'] for task in tasks]
        
        # Save metadata with execution plan
        self.table.put_item(Item={
            'investigation_id': investigation_id,
            'item_type': 'METADATA',
            'alarm_summary': alarm_summary,
            'execution_plan': {
                'current_task': task_ids[0] if task_ids else None,
                'completed_tasks': [],
                'pending_tasks': task_ids
            },
            'status': 'PENDING',
            'created_at': timestamp,
            'updated_at': timestamp
        })
        
        # Save tasks
        for task in tasks:
            self.table.put_item(Item={
                'investigation_id': investigation_id,
                'item_type': f"TASK#{task['task_id']}",
                'task_id': task['task_id'],
                'agent_type': task['agent_type'],
                'description': task['description'],
                'priority': task['priority'],
                'status': 'PENDING',
                'created_at': timestamp
            })
    
    def get_workflow(self, investigation_id: str) -> Dict:
        """Get investigation workflow from DynamoDB.
        
        Args:
            investigation_id: Investigation ID
            
        Returns:
            Dict with investigation_id, metadata, status, and tasks
        """
        response = self.table.query(
            KeyConditionExpression='investigation_id = :id',
            ExpressionAttributeValues={':id': investigation_id}
        )
        
        items = response.get('Items', [])
        metadata = next((i for i in items if i['item_type'] == 'METADATA'), {})
        tasks = [i for i in items if i['item_type'].startswith('TASK#')]
        
        return {
            'investigation_id': investigation_id,
            'alarm_summary': metadata.get('alarm_summary', {}),
            'status': metadata.get('status', 'UNKNOWN'),
            'tasks': tasks
        }
    
    def get_next_task(self, investigation_id: str) -> Optional[Dict]:
        """Get the next task to execute.
        
        Args:
            investigation_id: Investigation ID
            
        Returns:
            Task dict or None if no pending tasks
        """
        # Get metadata
        response = self.table.get_item(
            Key={
                'investigation_id': investigation_id,
                'item_type': 'METADATA'
            }
        )
        
        metadata = response.get('Item', {})
        execution_plan = metadata.get('execution_plan', {})
        current_task_id = execution_plan.get('current_task')
        
        log("get-next-task", f"current_task_id={current_task_id}, execution_plan={execution_plan}", investigation_id=investigation_id)
        
        if not current_task_id:
            log("get-next-task", "No current task found", investigation_id=investigation_id)
            return None
        
        # Get current task
        task_response = self.table.get_item(
            Key={
                'investigation_id': investigation_id,
                'item_type': f"TASK#{current_task_id}"
            }
        )
        
        task = task_response.get('Item')
        log("get-next-task", f"Retrieved task: {task.get('task_id') if task else None}", investigation_id=investigation_id)
        
        return task
    
    def complete_task(self, investigation_id: str, task_id: str, result: Dict) -> None:
        """Mark task as completed and move to next task.
        
        Args:
            investigation_id: Investigation ID
            task_id: Task ID
            result: Task result dict
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Get current metadata
        response = self.table.get_item(
            Key={
                'investigation_id': investigation_id,
                'item_type': 'METADATA'
            }
        )
        
        metadata = response.get('Item', {})
        execution_plan = metadata.get('execution_plan', {})
        
        # Update execution plan
        completed = execution_plan.get('completed_tasks', [])
        pending = execution_plan.get('pending_tasks', [])
        
        log("complete-task", f"task_id={task_id}, pending={pending}, completed={completed}", investigation_id=investigation_id)
        
        completed.append(task_id)
        if task_id in pending:
            pending.remove(task_id)
        
        next_task = pending[0] if pending else None
        new_status = 'PENDING' if next_task else 'COMPLETED'
        
        log("complete-task", f"next_task={next_task}, new_status={new_status}, pending_after={pending}", investigation_id=investigation_id)
        
        # Update metadata
        self.table.update_item(
            Key={
                'investigation_id': investigation_id,
                'item_type': 'METADATA'
            },
            UpdateExpression='SET execution_plan = :plan, updated_at = :timestamp, #st = :status',
            ExpressionAttributeNames={'#st': 'status'},
            ExpressionAttributeValues={
                ':plan': {
                    'current_task': next_task,
                    'completed_tasks': completed,
                    'pending_tasks': pending
                },
                ':status': new_status,
                ':timestamp': timestamp
            }
        )
        
        log("complete-task", f"Metadata updated: current_task={next_task}, status={new_status}", investigation_id=investigation_id)
        
        # Update or create task status
        self.table.update_item(
            Key={
                'investigation_id': investigation_id,
                'item_type': f"TASK#{task_id}"
            },
            UpdateExpression='SET updated_at = :timestamp, #st = :status',
            ExpressionAttributeNames={'#st': 'status'},
            ExpressionAttributeValues={
                ':status': 'COMPLETED',
                ':timestamp': timestamp
            }
        )
        
        # Save result
        self.table.put_item(Item={
            'investigation_id': investigation_id,
            'item_type': f"RESULT#{task_id}",
            'task_id': task_id,
            'result': result,
            'created_at': timestamp
        })
    
    def delete_investigation(self, investigation_id: str) -> None:
        """Delete all items for an investigation.
        
        Args:
            investigation_id: Investigation ID
        """
        # Query all items for this investigation
        response = self.table.query(
            KeyConditionExpression='investigation_id = :id',
            ExpressionAttributeValues={':id': investigation_id}
        )
        
        # Delete all items
        with self.table.batch_writer() as batch:
            for item in response.get('Items', []):
                batch.delete_item(
                    Key={
                        'investigation_id': item['investigation_id'],
                        'item_type': item['item_type']
                    }
                )
    
    def remove_tasks(self, investigation_id: str, task_ids: List[str]) -> int:
        """Remove pending tasks from investigation and reorganize IDs.
        
        Args:
            investigation_id: Investigation ID
            task_ids: List of task IDs to remove
            
        Returns:
            Number of tasks removed
        """
        # Get current metadata
        response = self.table.get_item(
            Key={
                'investigation_id': investigation_id,
                'item_type': 'METADATA'
            }
        )
        
        metadata = response.get('Item', {})
        execution_plan = metadata.get('execution_plan', {})
        pending = execution_plan.get('pending_tasks', [])
        
        # Get remaining tasks
        remaining_tasks = []
        removed = 0
        for task_id in pending:
            if task_id in task_ids:
                removed += 1
                self.table.delete_item(
                    Key={
                        'investigation_id': investigation_id,
                        'item_type': f"TASK#{task_id}"
                    }
                )
            else:
                task_response = self.table.get_item(
                    Key={
                        'investigation_id': investigation_id,
                        'item_type': f"TASK#{task_id}"
                    }
                )
                if 'Item' in task_response:
                    remaining_tasks.append(task_response['Item'])
        
        # Reorganize remaining tasks
        remaining_tasks.sort(key=lambda x: int(x.get('priority', 999)))
        
        # Delete old items
        for task in remaining_tasks:
            self.table.delete_item(
                Key={
                    'investigation_id': investigation_id,
                    'item_type': f"TASK#{task['task_id']}"
                }
            )
        
        # Reassign sequential IDs
        new_pending = []
        timestamp = datetime.utcnow().isoformat()
        for i, task in enumerate(remaining_tasks, 1):
            new_task_id = str(i)
            new_pending.append(new_task_id)
            
            self.table.put_item(Item={
                'investigation_id': investigation_id,
                'item_type': f"TASK#{new_task_id}",
                'task_id': new_task_id,
                'agent_type': task['agent_type'],
                'description': task['description'],
                'priority': task.get('priority', 999),
                'status': 'PENDING',
                'created_at': task.get('created_at', timestamp)
            })
        
        # Update metadata
        self.table.update_item(
            Key={
                'investigation_id': investigation_id,
                'item_type': 'METADATA'
            },
            UpdateExpression='SET execution_plan = :plan, updated_at = :timestamp',
            ExpressionAttributeValues={
                ':plan': {
                    'current_task': new_pending[0] if new_pending else None,
                    'completed_tasks': execution_plan.get('completed_tasks', []),
                    'pending_tasks': new_pending
                },
                ':timestamp': timestamp
            }
        )
        
        return removed
    
    def mark_task_failed(self, investigation_id: str, task_id: str, error: str) -> None:
        """Mark task as failed without moving to next task.
        
        Args:
            investigation_id: Investigation ID
            task_id: Task ID
            error: Error message
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Update task status to FAILED
        self.table.update_item(
            Key={
                'investigation_id': investigation_id,
                'item_type': f"TASK#{task_id}"
            },
            UpdateExpression='SET #st = :status, error = :error, updated_at = :timestamp',
            ExpressionAttributeNames={'#st': 'status'},
            ExpressionAttributeValues={
                ':status': 'FAILED',
                ':error': error,
                ':timestamp': timestamp
            }
        )
        
        # Save error as result
        self.table.put_item(Item={
            'investigation_id': investigation_id,
            'item_type': f"RESULT#{task_id}",
            'task_id': task_id,
            'result': {'error': error, 'status': 'failed'},
            'created_at': timestamp
        })
        
        log("mark-task-failed", f"Task {task_id} marked as FAILED: {error}", investigation_id=investigation_id)
    
    def update_task_description(self, investigation_id: str, task_id: str, new_description: str) -> bool:
        """Update description of a pending task.
        
        Args:
            investigation_id: Investigation ID
            task_id: Task ID to update
            new_description: New task description
            
        Returns:
            True if updated successfully
        """
        try:
            self.table.update_item(
                Key={
                    'investigation_id': investigation_id,
                    'item_type': f"TASK#{task_id}"
                },
                UpdateExpression='SET description = :desc, updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':desc': new_description,
                    ':timestamp': datetime.utcnow().isoformat()
                },
                ConditionExpression='attribute_exists(investigation_id)'
            )
            return True
        except Exception as e:
            print(f"Error updating task {task_id}: {e}")
            return False
    
    def add_tasks(self, investigation_id: str, tasks: List[Dict], reorganize: bool = True) -> int:
        """Add new tasks to investigation and reorganize task IDs.
        
        Args:
            investigation_id: Investigation ID
            tasks: List of new tasks with agent_type, description, priority
            reorganize: Whether to reorganize all task IDs in sequence
            
        Returns:
            Number of tasks added
        """
        # Get current workflow
        response = self.table.get_item(
            Key={
                'investigation_id': investigation_id,
                'item_type': 'METADATA'
            }
        )
        
        metadata = response.get('Item', {})
        execution_plan = metadata.get('execution_plan', {})
        pending = execution_plan.get('pending_tasks', [])
        
        # Get existing pending tasks
        existing_tasks = []
        for task_id in pending:
            task_response = self.table.get_item(
                Key={
                    'investigation_id': investigation_id,
                    'item_type': f"TASK#{task_id}"
                }
            )
            if 'Item' in task_response:
                existing_tasks.append(task_response['Item'])
        
        # Add new tasks with temporary IDs
        timestamp = datetime.utcnow().isoformat()
        for i, task in enumerate(tasks):
            task['task_id'] = f"new-{i+1}"
            existing_tasks.append({
                'task_id': task['task_id'],
                'agent_type': task['agent_type'],
                'description': task['description'],
                'priority': task.get('priority', 999),
                'status': 'PENDING',
                'created_at': timestamp
            })
        
        if reorganize:
            # Sort by priority
            existing_tasks.sort(key=lambda x: int(x.get('priority', 999)))
            
            # Delete old task items
            for task_id in pending:
                self.table.delete_item(
                    Key={
                        'investigation_id': investigation_id,
                        'item_type': f"TASK#{task_id}"
                    }
                )
            
            # Reassign sequential IDs and save
            new_pending = []
            for i, task in enumerate(existing_tasks, 1):
                new_task_id = str(i)
                new_pending.append(new_task_id)
                
                self.table.put_item(Item={
                    'investigation_id': investigation_id,
                    'item_type': f"TASK#{new_task_id}",
                    'task_id': new_task_id,
                    'agent_type': task['agent_type'],
                    'description': task['description'],
                    'priority': task.get('priority', 999),
                    'status': 'PENDING',
                    'created_at': task.get('created_at', timestamp)
                })
            
            # Update metadata with reorganized task list
            self.table.update_item(
                Key={
                    'investigation_id': investigation_id,
                    'item_type': 'METADATA'
                },
                UpdateExpression='SET execution_plan = :plan, updated_at = :timestamp',
                ExpressionAttributeValues={
                    ':plan': {
                        'current_task': new_pending[0] if new_pending else None,
                        'completed_tasks': execution_plan.get('completed_tasks', []),
                        'pending_tasks': new_pending
                    },
                    ':timestamp': timestamp
                }
            )
        
        return len(tasks)
