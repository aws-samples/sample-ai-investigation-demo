"""
You are a observability trace graph analysis expert. Your role is to:
    
    1. Get the service graph from X-Ray for the last 15 minutes to understand the service topology and identify problematic nodes.
    Use the get_xray_service_graph tool to get the service graph for the last 15 minutes.
    Use the analyze_xray_service_graph tool to analyze the service graph and identify relevant nodes.

    2. Analyze the service graph to identify the most relevant trace nodes that are related to the errors. Look for:
       - Services with high error rates (4xx, 5xx responses)
       - Services with high latency
       - Services that are downstream dependencies of the alerting service
       - Services that match the alarm context and resource information

    3. Determine the most relevant service nodes (limit to 1-2 services) that should be investigated further for trace summaries.
    
    4. Generate filter criteria for getting trace summaries from the identified problematic services. The filter should target error traces (error = true or fault = true) for the specific services.

    Use the alarm analysis provided by the previous nodes to guide your trace graph investigation.
    The alarm analysis contains information about the identified alarm type and relevant troubleshooting steps.
    
    The output should be a structured JSON response containing:
    - trace_graph_analysis: structured JSON with the following
        - service_graph: Relevant service graph data from X-Ray
            - root_service_name: Name of the root service in the graph
            - root_service_type: Type of the root service (e.g., AWS::ApiGateway::Stage)
            - total_services: Total number of services in the graph
            - total_requests: Total number of requests in the graph
            - error_rate: Overall error rate percentage for the service graph
        - relevant_nodes: List of most relevant trace nodes for investigation with the following attributes:
            - service_name: Name of the service
            - service_type: Type of the service (e.g., AWS::EC2::Instance)
            - error_rate: Error rate percentage if available
            - latency: Average latency if available
            - reason: Reason for selecting this node for investigation
    - raw_analysis: Summary of trace graph analysis explaining the selection rationale
    - recommended_services: List of service names recommended for detailed trace investigation

"""

import sys
import os
import json
from langchain_core.messages import AIMessage

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import get_bedrock_model, create_prompt_template, create_agent_executor, COMMON_TOOLS

# Import the X-Ray service graph tool
from tools.xray_service_graph_tool import get_xray_service_graph, analyze_xray_service_graph

from agents.agent import Agent

# Import constants
from constants import ContextKeys, AnalysisKeys

class TraceGraphAnalyzerAgent(Agent):
    """Trace Graph Analyzer Agent for service graph analysis"""
    
    def __init__(self):
        """Initialize the Trace Graph Analyzer Agent"""
        super().__init__("Trace Graph Analyzer Agent")
        self.prompt = create_prompt_template("Trace Graph Analyzer Agent", __doc__)
        
        # Add the X-Ray service graph tools to the common tools
        xray_tools = [get_xray_service_graph, analyze_xray_service_graph]
        all_tools = COMMON_TOOLS + xray_tools
        
        self.agent_executor = create_agent_executor(self.model, all_tools, self.prompt)
    
    def process(self, input_data):
        """
        Process the input data and return trace graph analysis
        
        Args:
            input_data: Input data containing alarm and decision information
            
        Returns:
            Dict containing trace graph analysis results
        """
        try:
            # Let the agent handle the X-Ray service graph analysis
            result = self.agent_executor.invoke({
                "input": f"Analyze the service graph and identify most relevant trace nodes for investigation:\n\n{input_data}"
            })
            
            return result["output"]
        except Exception as e:
            # If agent fails, provide a proper error response
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error invoking trace graph analyzer agent: {e}", exc_info=True)
            
            # Create a proper JSON error response
            error_response = {
                "trace_graph_analysis": {
                    "service_graph": {
                        "root_service_name": "unknown",
                        "root_service_type": "unknown",
                        "total_services": 0,
                        "total_requests": 0,
                        "error_rate": 0
                    },
                    "relevant_nodes": [],
                    "filter_criteria": ""
                },
                "raw_analysis": f"Trace graph analysis failed: {str(e)}",
                "recommended_services": []
            }
            
            return json.dumps(error_response)

# Legacy function for backward compatibility
def create_trace_graph_analyzer_agent():
    """Create a trace graph analyzer agent"""
    return TraceGraphAnalyzerAgent()
