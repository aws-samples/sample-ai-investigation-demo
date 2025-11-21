"""Enums for the AIOps Root Cause Analysis system"""

from enum import Enum


class MessageType(str, Enum):
    """SQS message types for different agent execution flows"""
    ALARM = "ALARM"           # Consumed by Brain Agent
    EXECUTION = "EXECUTION"   # Consumed by Executor Agent
    EVALUATION = "EVALUATION" # Consumed by Evaluator Agent


class ExecutionStatus(Enum):
    """Status of workflow step execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class InvestigationStatus(Enum):
    """Status of investigation process"""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    AWAITING_EVALUATION = "awaiting_evaluation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvidenceType(Enum):
    """Type of evidence collected during investigation"""
    METRIC_DATA = "metric_data"
    LOG_ENTRY = "log_entry"
    CONFIGURATION = "configuration"
    NETWORK_TRACE = "network_trace"
    SYSTEM_STATE = "system_state"
    ERROR_MESSAGE = "error_message"
    PERFORMANCE_DATA = "performance_data"
    DEPENDENCY_CHECK = "dependency_check"


class AgentType(Enum):
    """Type of agent in the system"""
    BRAIN = "brain"
    EXECUTOR = "executor"
    EVALUATOR = "evaluator"
    TOOL = "tool"