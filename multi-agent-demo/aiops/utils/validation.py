"""Validation utilities for data models"""

from typing import List, Dict, Any
from ..models.data_models import AlarmInput, InvestigationWorkflow, WorkflowStep


class AlarmValidator:
    """Validator for AWS CloudWatch alarm data"""
    
    VALID_ALARM_STATES = ['OK', 'ALARM', 'INSUFFICIENT_DATA']
    VALID_COMPARISON_OPERATORS = [
        'GreaterThanThreshold', 'GreaterThanOrEqualToThreshold',
        'LessThanThreshold', 'LessThanOrEqualToThreshold'
    ]
    
    @classmethod
    def validate_alarm_input(cls, alarm_input: AlarmInput) -> tuple[bool, List[str]]:
        """Validate alarm input and return validation result with errors"""
        errors = []
        
        # Check required fields
        required_fields = {
            'alarm_name': alarm_input.alarm_name,
            'metric_name': alarm_input.metric_name,
            'namespace': alarm_input.namespace,
            'alarm_state': alarm_input.alarm_state,
            'region': alarm_input.region
        }
        
        for field_name, value in required_fields.items():
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(f"Required field '{field_name}' is missing or empty")
        
        # Validate alarm state
        if alarm_input.alarm_state not in cls.VALID_ALARM_STATES:
            errors.append(f"Invalid alarm state: {alarm_input.alarm_state}. "
                         f"Must be one of: {cls.VALID_ALARM_STATES}")
        
        # Validate comparison operator
        if alarm_input.comparison_operator not in cls.VALID_COMPARISON_OPERATORS:
            errors.append(f"Invalid comparison operator: {alarm_input.comparison_operator}. "
                         f"Must be one of: {cls.VALID_COMPARISON_OPERATORS}")
        
        # Validate numeric fields
        if alarm_input.evaluation_periods <= 0:
            errors.append("Evaluation periods must be greater than 0")
        
        if alarm_input.datapoints_to_alarm <= 0:
            errors.append("Datapoints to alarm must be greater than 0")
        
        # Validate dimensions
        if not isinstance(alarm_input.dimensions, dict):
            errors.append("Dimensions must be a dictionary")
        
        return len(errors) == 0, errors


class WorkflowValidator:
    """Validator for investigation workflows"""
    
    @classmethod
    def validate_workflow(cls, workflow: InvestigationWorkflow) -> tuple[bool, List[str]]:
        """Validate workflow and return validation result with errors"""
        errors = []
        
        # Check required fields
        if not workflow.workflow_id:
            errors.append("Workflow ID is required")
        
        if not workflow.steps:
            errors.append("Workflow must contain at least one step")
        
        if not workflow.priority:
            errors.append("Workflow priority is required")
        
        if workflow.estimated_duration <= 0:
            errors.append("Estimated duration must be greater than 0")
        
        # Validate individual steps
        step_ids = set()
        for i, step in enumerate(workflow.steps):
            step_errors = cls._validate_workflow_step(step, i)
            errors.extend(step_errors)
            
            # Check for duplicate step IDs
            if step.step_id in step_ids:
                errors.append(f"Duplicate step ID: {step.step_id}")
            step_ids.add(step.step_id)
        
        # Validate step dependencies
        dependency_errors = cls._validate_step_dependencies(workflow.steps)
        errors.extend(dependency_errors)
        
        return len(errors) == 0, errors
    
    @classmethod
    def _validate_workflow_step(cls, step: WorkflowStep, index: int) -> List[str]:
        """Validate individual workflow step"""
        errors = []
        
        if not step.step_id:
            errors.append(f"Step {index}: Step ID is required")
        
        if not step.description:
            errors.append(f"Step {index}: Description is required")
        
        if not step.expected_output:
            errors.append(f"Step {index}: Expected output is required")
        
        if not isinstance(step.required_data, list):
            errors.append(f"Step {index}: Required data must be a list")
        
        if not isinstance(step.dependencies, list):
            errors.append(f"Step {index}: Dependencies must be a list")
        
        return errors
    
    @classmethod
    def _validate_step_dependencies(cls, steps: List[WorkflowStep]) -> List[str]:
        """Validate step dependencies are valid"""
        errors = []
        step_ids = {step.step_id for step in steps}
        
        for step in steps:
            for dependency in step.dependencies:
                if dependency not in step_ids:
                    errors.append(f"Step {step.step_id}: Invalid dependency '{dependency}' - "
                                f"step does not exist in workflow")
        
        return errors