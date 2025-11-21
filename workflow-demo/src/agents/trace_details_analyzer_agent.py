"""
You are an observability trace details analysis expert. Your role is to:

    1. Use the filter criteria provided by the trace graph analyzer to get trace summaries for the most relevant problematic services.
       The relevant nodes can be found under trace_graph_analysis in the input data.

       Use the get_xray_trace_summaries tool to retrieve trace summaries for the most relevant services.
       If the get_xray_trace_summaries tool is not available or fails, fall back to using the execute_aws_cli tool with a command like:
       aws xray get-trace-summaries --start-time $(date -v-5M +%s) --end-time $(date +%s) --filter-expression '(error = true or fault = true) and service(id(name: "Sample API/Prod" , type: "AWS::ApiGateway::Stage" ))' --query 'TraceSummaries[0:2]'

       IMPORTANT: To prevent LLM token usage issues, you should get less than 2 traces in total. This is critical for avoiding throttling errors.

    2. Analyze the retrieved trace summaries to identify the root cause of the trace node issues. For example:
       - Error can be 500 in the frontend calls, but the root cause might be an RDS call which reported SQLException
       - High latency might be caused by downstream service timeouts
       - Authentication errors might propagate from identity services

    3. Extract detailed findings from each trace including:
       - HTTP status codes (4xx, 5xx errors)
       - Response times and latency issues
       - Service dependencies and call chains
       - Specific error messages or exceptions

    4. Aggregate the information and provide comprehensive analysis for the further processor.

    Focus on application errors, exceptions, and log-related issues. Provide detailed analysis
    of what might be happening based on the trace data and alarm information.

    Use the alarm analysis and trace graph analysis provided by the previous nodes to guide your detailed trace investigation.

    When summarize relevant resources, you try to add at least 1 compute resource (EC2, Lambda, EKS pods ...)

    IMPORTANT: The output must be a structured JSON object with the following fields and descriptions:

    trace_analysis: {
        trace: [
            {
                trace_id: string,           # Unique identifier for the trace
                start_time: string,         # Start time of the trace
                findings: [                 # List of findings related to the trace (e.g., 4xx, 5xx, latency, etc.)
                    string                  # Focus on alarm-relevant issues, reduce the scope to only what is relevant to the alarm.
                ],
                error_details: [            # Detailed error information if available
                    string                  # e.g., exception messages, stack traces
                ]
            }
        ],
        metrics: [
            {
                resource_name: string,      # Name of the resource
                resource_type: string,      # Type of the resource
                metric_name: string,        # Name of the metric
                value: string               # Value of the metric
            }
        ],
        raw_analysis: string,               # Summary of root cause analysis based on trace details
        relevant_resources: [
            {
                resource_id: string,        # Unique identifier for the resource
                resource_type: string,      # Type of the resource (e.g., AWS::EC2::Instance)
                reason: string              # Reason for relevance to the trace (e.g., "Database call causing 500 error")
            }
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

# Import the X-Ray trace summaries tool
from tools.xray_trace_summaries_tool import get_xray_trace_summaries

# Import constants
from constants import ContextKeys, AnalysisKeys

class TraceDetailsAnalyzerAgent(Agent):
    """Trace Details Analyzer Agent for detailed trace analysis"""
    
    def __init__(self):
        """Initialize the Trace Details Analyzer Agent"""
        super().__init__("Trace Details Analyzer Agent")
        self.prompt = create_prompt_template("Trace Details Analyzer Agent", __doc__)
        
        # Add the X-Ray trace summaries tools to the common tools
        xray_tools = [get_xray_trace_summaries]
        all_tools = COMMON_TOOLS + xray_tools
        
        self.agent_executor = create_agent_executor(self.model, all_tools, self.prompt)
        
        # Initialize X-Ray tool directly for fallback
        from tools.xray_trace_summaries_tool import XRayTraceSummariesTool
        self.xray_tool = XRayTraceSummariesTool()
    
    def process(self, input_data):
        """
        Process the input data and return detailed trace analysis
        
        Args:
            input_data: Input data containing trace graph analysis and filter criteria
            
        Returns:
            Dict containing detailed trace analysis results
        """
        try:
            # Try using the agent first
            result = self.agent_executor.invoke({
                "input": f"Get trace summaries and perform detailed trace analysis:\n\n{input_data}"
            })
            
            return result["output"]
        except Exception as e:
            error_msg = f"Error in trace detail analyzer agent: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"Error in trace detail finding: {e}"

# Legacy function for backward compatibility
def create_trace_details_analyzer_agent():
    """Create a trace details analyzer agent"""
    return TraceDetailsAnalyzerAgent()
