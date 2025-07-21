"""
Root Cause Analysis Agent - Performs comprehensive root cause analysis

Responsible for:
1. Analyzing all collected data to identify the root cause of issues
2. Correlating information from multiple sources (traces, metrics, logs, resources)
3. Applying analytical reasoning to determine causal relationships
4. Providing confidence scores for identified root causes
5. Recommending specific remediation actions
6. Identifying contributing factors and systemic issues

The agent synthesizes information from the entire investigation workflow to provide
definitive root cause analysis with actionable recommendations.

Response output MUST be strictly in JSON format with the following structure:
{
    "root_cause_analysis": {
        "identified_cause": "Primary root cause description",
        "confidence_score": 0.85,
        "category": "performance|configuration|resource|code|external",
        "severity_assessment": "critical|high|medium|low",
        "impact_scope": "service|application|infrastructure|organization"
    },
    "contributing_factors": [
        {
            "factor": "High memory usage",
            "impact_level": "high|medium|low",
            "evidence": "Memory utilization at 95% for 30 minutes"
        }
    ],
    "evidence_analysis": [
        {
            "source": "cloudwatch_metrics",
            "finding": "CPU utilization exceeded 90% threshold",
            "relevance": "direct|indirect|supporting",
            "timestamp": "2025-06-10T02:00:00Z"
        }
    ],
    "recommended_actions": [
        {
            "action": "Scale up EC2 instance type",
            "priority": "immediate|high|medium|low",
            "expected_impact": "Reduce CPU utilization by 40%",
            "estimated_effort": "15 minutes",
            "risk_level": "low|medium|high"
        }
    ],
    "prevention_measures": [
        "Implement auto-scaling policies",
        "Set up proactive monitoring alerts",
        "Regular capacity planning reviews"
    ]
}
"""

import sys
import os
import json
from langchain_core.messages import AIMessage

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import create_prompt_template, create_agent_executor, COMMON_TOOLS
from agents.agent import Agent

class RootCauseAnalysisAgent(Agent):
    """Root Cause Analysis Agent for comprehensive issue analysis"""
    
    def __init__(self):
        """Initialize the Root Cause Analysis Agent"""
        super().__init__("Root Cause Analysis Agent")
        self.prompt = create_prompt_template("Root Cause Analysis Agent", __doc__)
        self.agent_executor = create_agent_executor(self.model, COMMON_TOOLS, self.prompt)
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)
    
    def process(self, input_data):
        """
        Process the input data and return root cause analysis
        
        Args:
            input_data: Input data containing all collected investigation information
            
        Returns:
            Dict containing comprehensive root cause analysis
        """
        # Use direct model invocation as primary method to avoid XML parser issues
        self.logger.info("Starting root cause analysis with direct model invocation")
        
        try:
            from util import model_direct_invoke_json
            
            # Create a structured prompt for direct model invocation
            direct_prompt = f"""
            You are an expert AWS root cause analysis specialist. Analyze the following investigation data and provide a comprehensive root cause analysis.

            Investigation Data:
            {input_data}

            Please provide your analysis in the following JSON format:
            {{
                "root_cause_summary": "Brief summary of the root cause",
                "primary_cause": "The main cause of the issue",
                "contributing_factors": ["factor1", "factor2", "factor3"],
                "evidence": ["evidence1", "evidence2", "evidence3"],
                "impact_assessment": {{
                    "severity": "High|Medium|Low",
                    "affected_services": ["service1", "service2"],
                    "business_impact": "Description of business impact"
                }},
                "resolution_steps": [
                    "Step 1: Immediate action",
                    "Step 2: Short-term fix",
                    "Step 3: Long-term prevention"
                ],
                "prevention_measures": [
                    "Preventive measure 1",
                    "Preventive measure 2"
                ],
                "monitoring_recommendations": [
                    "Monitoring recommendation 1",
                    "Monitoring recommendation 2"
                ]
            }}
            """
            
            # Use direct model invocation with JSON parsing
            result = model_direct_invoke_json(direct_prompt, max_tokens=6000)
            
            if 'error' not in result:
                # Convert the JSON result to the expected string format
                import json
                self.logger.info("Direct model invocation successful")
                return json.dumps(result, indent=2)
            else:
                # If JSON parsing fails, use quick invocation
                self.logger.warning(f"JSON parsing failed: {result['error']}")
                self.logger.info("Falling back to quick text analysis")
                
                from util import model_direct_invoke_quick
                
                quick_prompt = f"""
                Analyze this AWS incident data and provide a comprehensive root cause analysis:
                
                {input_data}
                
                Include:
                1. Root cause summary
                2. Primary cause
                3. Contributing factors
                4. Evidence
                5. Resolution steps
                6. Prevention measures
                """
                
                return model_direct_invoke_quick(quick_prompt, max_tokens=4000)
                
        except Exception as direct_error:
            self.logger.error(f"Direct model invocation failed: {direct_error}")
            self.logger.info("Attempting LangChain agent as fallback")
            
            # Try the original agent executor as fallback
            try:
                result = self.agent_executor.invoke({
                    "input": f"Perform comprehensive root cause analysis on this investigation data:\n\n{input_data}"
                })
                
                return result["output"]
                
            except Exception as agent_error:
                self.logger.error(f"Agent executor also failed: {agent_error}")
                
                # Ultimate fallback - return a structured error response
                import json
                return json.dumps({
                    "root_cause_summary": "Analysis failed due to technical issues",
                    "primary_cause": "Unable to determine due to processing error",
                    "contributing_factors": ["Technical processing error"],
                    "evidence": ["Error in analysis pipeline"],
                    "impact_assessment": {
                        "severity": "Unknown",
                        "affected_services": ["Unknown"],
                        "business_impact": "Unable to assess due to analysis failure"
                    },
                    "resolution_steps": [
                        "Review system logs for analysis pipeline errors",
                        "Retry analysis with manual intervention",
                        "Escalate to technical team for investigation"
                    ],
                    "prevention_measures": [
                        "Improve error handling in analysis pipeline",
                        "Add monitoring for analysis system health"
                    ],
                    "monitoring_recommendations": [
                        "Monitor analysis system performance",
                        "Set up alerts for analysis failures"
                    ],
                    "error": f"Analysis failed: Direct model error: {str(direct_error)}, Agent error: {str(agent_error)}"
                }, indent=2)
