"""
Trace Finder Agent - Specialized agent for finding and analyzing trace data

Responsible for:
1. Finding problematic traces related to the alarm/issue
2. Analyzing trace summaries to identify error patterns
3. Extracting relevant metrics from traces (4xx, 5xx, latency, etc.)
4. Identifying resources involved in problematic traces
5. Providing structured trace analysis for downstream processing

The agent receives structured input containing:
1. Decision analysis data with alert type and resource information
2. Alarm analysis context with severity and details
3. Initial decision context for processing guidance

The agent must retrieve and analyze:
- Problematic trace summaries from X-Ray or other tracing systems
- Error patterns and metrics from traces
- Resource involvement and dependencies
- Root cause indicators from trace data

Output format:
    - trace_analysis: structured JSON with the following
        - trace: List of problematic trace summaries
        - metrics: list of facts of the trace node, e.g. 4xx, 5xx, latency, etc.
    - raw_analysis: Summary of root cause analysis
    - relevant_resources: List of resources involved in the trace
"""

import sys
import os
import json
from langchain_core.messages import AIMessage

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import get_bedrock_model, create_prompt_template, create_agent_executor, COMMON_TOOLS
from agents.agent import Agent

# Import constants
from constants import ContextKeys, AnalysisKeys

class TraceFinderAgent(Agent):
    """Trace Finder Agent for trace data discovery and analysis"""
    
    def __init__(self):
        """Initialize the Trace Finder Agent"""
        super().__init__("Trace Finder Agent")
        
        # Initialize the agent executor
        self.agent_executor = create_trace_finder()
    
    def process(self, input_data):
        """Process the input and return trace analysis results"""
        try:
            result = self.agent_executor.invoke({
                "input": input_data
            })
            
            # Extract the output from the result
            if isinstance(result, dict) and "output" in result:
                return result["output"]
            else:
                return str(result)
                
        except Exception as e:
            error_msg = f"Error in trace finder agent: {e}"
            self.logger.error(error_msg, exc_info=True)
            return f"Error in trace finding: {e}"

def create_trace_finder():
    """Create and return a trace finder agent"""
    model = get_bedrock_model(1, 150000)
    prompt = create_prompt_template("Trace Finder Agent", __doc__)
    return create_agent_executor(model, COMMON_TOOLS, prompt)
