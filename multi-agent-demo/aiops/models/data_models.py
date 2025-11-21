"""Core data models for the AIOps Root Cause Analysis system"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from .enums import ExecutionStatus, InvestigationStatus, EvidenceType, AgentType


@dataclass
class AlarmInput:
    """AWS CloudWatch alarm input data"""
    alarm_name: str
    alarm_description: str
    metric_name: str
    namespace: str
    dimensions: Dict[str, str]
    threshold: float
    comparison_operator: str
    evaluation_periods: int
    datapoints_to_alarm: int
    alarm_state: str
    state_reason: str
    timestamp: datetime
    region: str
    
    def validate(self) -> bool:
        """Validate AWS CloudWatch alarm format"""
        required_fields = [
            'alarm_name', 'metric_name', 'namespace', 'threshold',
            'comparison_operator', 'alarm_state', 'region'
        ]
        
        # Check required fields are not empty
        for field_name in required_fields:
            if not getattr(self, field_name):
                return False
        
        # Validate alarm state
        valid_states = ['OK', 'ALARM', 'INSUFFICIENT_DATA']
        if self.alarm_state not in valid_states:
            return False
            
        # Validate comparison operator
        valid_operators = [
            'GreaterThanThreshold', 'GreaterThanOrEqualToThreshold',
            'LessThanThreshold', 'LessThanOrEqualToThreshold'
        ]
        if self.comparison_operator not in valid_operators:
            return False
            
        # Validate numeric fields
        if self.evaluation_periods <= 0 or self.datapoints_to_alarm <= 0:
            return False
            
        return True


@dataclass
class Evidence:
    """Evidence collected during investigation"""
    evidence_id: str
    type: EvidenceType
    source: str
    content: Dict[str, Any]
    reliability_score: float
    timestamp: datetime
    
    def __post_init__(self):
        """Validate evidence data after initialization"""
        if not 0.0 <= self.reliability_score <= 1.0:
            raise ValueError("Reliability score must be between 0.0 and 1.0")


@dataclass
class WorkflowStep:
    """Individual step in an investigation workflow"""
    step_id: str
    description: str
    agent_type: AgentType
    required_data: List[str]
    expected_output: str
    dependencies: List[str] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate workflow step data"""
        return bool(self.step_id and self.description and self.expected_output)


@dataclass
class ExecutionResult:
    """Result of executing a workflow step"""
    step_id: str
    status: ExecutionStatus
    findings: Dict[str, Any]
    confidence_score: float
    next_recommended_steps: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Validate execution result data after initialization"""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")


@dataclass
class InvestigationWorkflow:
    """Complete investigation workflow"""
    workflow_id: str
    steps: List[WorkflowStep]
    priority: str
    estimated_duration: int
    required_tools: List[str] = field(default_factory=list)
    
    def validate(self) -> bool:
        """Validate workflow data"""
        if not self.workflow_id or not self.steps:
            return False
        return all(step.validate() for step in self.steps)


@dataclass
class RootCause:
    """Identified root cause candidate"""
    cause_id: str
    description: str
    probability: float
    supporting_evidence: List[str]
    mitigation_steps: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate root cause data after initialization"""
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("Probability must be between 0.0 and 1.0")


@dataclass
class InvestigationEvent:
    """Event that occurred during investigation"""
    event_id: str
    timestamp: datetime
    event_type: str
    description: str
    agent_id: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisReport:
    """Comprehensive analysis report from Brain Agent"""
    investigation_id: str
    root_cause_candidates: List[RootCause]
    supporting_evidence: List[Evidence]
    confidence_score: float
    investigation_timeline: List[InvestigationEvent]
    recommendations: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate analysis report data after initialization"""
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")


@dataclass
class Fact:
    """Consolidated fact from investigation"""
    fact_id: str
    description: str
    confidence: float
    sources: List[str]
    
    def __post_init__(self):
        """Validate fact data after initialization"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass
class Pattern:
    """Identified pattern in investigation data"""
    pattern_id: str
    description: str
    occurrences: int
    significance: float


@dataclass
class Correlation:
    """Correlation between investigation elements"""
    correlation_id: str
    element_a: str
    element_b: str
    strength: float
    description: str
    
    def __post_init__(self):
        """Validate correlation data after initialization"""
        if not -1.0 <= self.strength <= 1.0:
            raise ValueError("Correlation strength must be between -1.0 and 1.0")


@dataclass
class ConsolidatedFacts:
    """Consolidated facts for new investigation round"""
    facts: List[Fact]
    patterns: List[Pattern]
    correlations: List[Correlation]
    gaps: List[str] = field(default_factory=list)


@dataclass
class FinalReport:
    """Final investigation report"""
    investigation_id: str
    root_cause: RootCause
    confidence_score: float
    investigation_summary: str
    recommendations: List[str]
    investigation_duration: float
    rounds_completed: int


@dataclass
class EvaluationResult:
    """Result of investigation evaluation"""
    investigation_complete: bool
    quality_score: float
    missing_evidence: List[str] = field(default_factory=list)
    consolidated_facts: Optional[ConsolidatedFacts] = None
    final_report: Optional[FinalReport] = None
    
    def __post_init__(self):
        """Validate evaluation result data after initialization"""
        if not 0.0 <= self.quality_score <= 1.0:
            raise ValueError("Quality score must be between 0.0 and 1.0")


@dataclass
class ExecutionState:
    """State of workflow execution"""
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    current_step: Optional[str] = None
    aggregated_results: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionRequest:
    """Request to execute workflow"""
    workflow: InvestigationWorkflow
    current_context: Dict[str, Any]
    execution_state: ExecutionState


@dataclass
class InvestigationRound:
    """Single round of investigation"""
    round_id: str
    workflow: InvestigationWorkflow
    execution_results: List[ExecutionResult] = field(default_factory=list)
    analysis_report: Optional[AnalysisReport] = None
    evaluation_result: Optional[EvaluationResult] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None


@dataclass
class Investigation:
    """Complete investigation process"""
    investigation_id: str
    alarm_input: AlarmInput
    rounds: List[InvestigationRound] = field(default_factory=list)
    current_round: int = 0
    status: InvestigationStatus = InvestigationStatus.INITIATED
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def validate(self) -> bool:
        """Validate investigation data"""
        return bool(
            self.investigation_id and 
            self.alarm_input and 
            self.alarm_input.validate()
        )