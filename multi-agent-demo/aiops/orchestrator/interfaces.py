"""Agent interface definitions for the AIOps Root Cause Analysis system using Strands framework"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..models.data_models import (
    AlarmInput, InvestigationWorkflow, ExecutionRequest, ExecutionResult,
    AnalysisReport, EvaluationResult, Investigation
)


class StrandsAgentInterface(ABC):
    """Base interface for Strands-based agents"""
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass
    
    @abstractmethod
    def get_tools(self) -> List:
        """Get the tools for this agent"""
        pass
    
    @abstractmethod
    def process_request(self, request: str, **kwargs) -> str:
        """Process a request using the Strands agent"""
        pass


class BrainAgentInterface(StrandsAgentInterface):
    """Interface for Brain Agent functionality"""
    
    @abstractmethod
    def process_alarm(self, alarm_input: AlarmInput) -> Investigation:
        """Process AWS alarm and create initial investigation"""
        pass
    
    @abstractmethod
    def generate_workflow(self, investigation: Investigation) -> InvestigationWorkflow:
        """Generate investigation workflow based on alarm analysis"""
        pass
    
    @abstractmethod
    def update_workflow(self, workflow: InvestigationWorkflow, 
                       execution_results: List[ExecutionResult]) -> InvestigationWorkflow:
        """Update workflow based on execution results"""
        pass
    

    
    @abstractmethod
    def generate_analysis_report(self, investigation: Investigation) -> AnalysisReport:
        """Generate comprehensive analysis report"""
        pass
    
    @abstractmethod
    def process_consolidated_facts(self, investigation: Investigation, 
                                 consolidated_facts: dict) -> InvestigationWorkflow:
        """Process consolidated facts and generate new investigation round"""
        pass


class ExecutorAgentInterface(StrandsAgentInterface):
    """Interface for Executor Agent functionality"""
    
    @abstractmethod
    def execute_workflow(self, execution_request: ExecutionRequest) -> List[ExecutionResult]:
        """Execute complete investigation workflow"""
        pass
    
    @abstractmethod
    def execute_step(self, workflow_step: dict, context: dict) -> ExecutionResult:
        """Execute individual workflow step"""
        pass
    
    @abstractmethod
    def aggregate_results(self, execution_results: List[ExecutionResult]) -> dict:
        """Aggregate results from multiple workflow steps"""
        pass
    
    @abstractmethod
    def handle_step_failure(self, step_id: str, error: Exception) -> ExecutionResult:
        """Handle workflow step execution failure"""
        pass
    
    @abstractmethod
    def get_execution_progress(self, workflow_id: str) -> dict:
        """Get current execution progress for workflow"""
        pass


class EvaluatorAgentInterface(StrandsAgentInterface):
    """Interface for Evaluator Agent functionality"""
    
    @abstractmethod
    def evaluate_investigation(self, analysis_report: AnalysisReport) -> EvaluationResult:
        """Evaluate investigation completeness and quality"""
        pass
    
    @abstractmethod
    def assess_completeness(self, analysis_report: AnalysisReport) -> bool:
        """Assess if investigation is complete"""
        pass
    
    @abstractmethod
    def calculate_quality_score(self, analysis_report: AnalysisReport) -> float:
        """Calculate quality score for investigation"""
        pass
    
    @abstractmethod
    def consolidate_facts(self, investigation: Investigation) -> dict:
        """Consolidate facts from investigation for new round"""
        pass
    
    @abstractmethod
    def generate_final_report(self, investigation: Investigation) -> dict:
        """Generate final investigation report"""
        pass
    
    @abstractmethod
    def identify_missing_evidence(self, analysis_report: AnalysisReport) -> List[str]:
        """Identify missing evidence types"""
        pass