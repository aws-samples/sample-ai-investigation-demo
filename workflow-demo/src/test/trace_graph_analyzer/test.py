#!/usr/bin/env python3
"""
Trace graph analyzer node test using the simple base test framework
"""

import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_test import SimpleNodeTest
from langchain_core.messages import AIMessage
from constants import ContextKeys
import json

# Import the node function directly to avoid circular imports
import importlib.util
spec = importlib.util.spec_from_file_location(
    'trace_graph_analyzer_node', 
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'nodes', 'trace_graph_analyzer_node.py')
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
trace_graph_analyzer_node = module.trace_graph_analyzer_node

class TraceGraphAnalyzerTest(SimpleNodeTest):
    """Simple Trace Graph Analyzer node test"""
    
    def __init__(self):
        super().__init__(trace_graph_analyzer_node)
    
    def call_node(self, content):
        """Override to format content correctly for trace graph analyzer node"""
        # Trace graph analyzer expects decision node output in messages and alarm analysis in context
        # The sample file has structure: {"messages": [{"content": {...}}], "context": {"alarm_analysis": {...}}}
        
        if isinstance(content, dict):
            if "messages" in content and "context" in content:
                # Extract decision data from the sample file structure
                decision_data = content["messages"][0]["content"]
                alarm_analysis = content["context"]["alarm_analysis"]
                
                state = {
                    "messages": [AIMessage(content=json.dumps(decision_data))],
                    "context": {
                        ContextKeys.ALARM_ANALYSIS: alarm_analysis,
                        "trace_id": "test-trace-123"
                    }
                }
            else:
                # Treat content as decision data directly
                state = {
                    "messages": [AIMessage(content=json.dumps(content))],
                    "context": {
                        ContextKeys.ALARM_ANALYSIS: {
                            "identified_alarm_types": ["Performance Issue"],
                            "severity": "High"
                        },
                        "trace_id": "test-trace-123"
                    }
                }
        else:
            # Handle string or other content types
            state = {
                "messages": [AIMessage(content=str(content))],
                "context": {
                    ContextKeys.ALARM_ANALYSIS: {
                        "identified_alarm_types": ["Performance Issue"],
                        "severity": "High"
                    },
                    "trace_id": "test-trace-123"
                }
            }
        
        return super().call_node(state)
    
    def validate_response(self, response):
        """Validate Trace Graph Analyzer response"""
        print(f"Response keys: {list(response.keys())}")
        
        # Check if we have messages
        if "messages" not in response:
            print("❌ No messages in response")
            return False
        
        if not response["messages"]:
            print("❌ Empty messages list")
            return False
        
        # Parse the JSON response from messages
        try:
            message_content = response["messages"][0].content
            response_data = json.loads(message_content)
            print(f"Response data keys: {list(response_data.keys())}")
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in response: {e}")
            return False
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            return False
        
        # Check for required fields in trace graph analysis
        required_fields = [
            "trace_graph_analysis",
            "raw_analysis", 
            "recommended_services"
        ]
        
        found_fields = []
        for field in required_fields:
            if field in response_data:
                found_fields.append(field)
                print(f"   ✅ Found field: {field}")
            else:
                print(f"   ❌ Missing field: {field}")
        
        if len(found_fields) != len(required_fields):
            print(f"❌ Missing required fields. Found {len(found_fields)}/{len(required_fields)}")
            return False
        
        # Validate trace_graph_analysis structure
        trace_analysis = response_data["trace_graph_analysis"]
        if isinstance(trace_analysis, dict):
            print("✅ trace_graph_analysis is a dictionary")
            
            # Check for service_graph and relevant_nodes
            analysis_fields = ["service_graph", "relevant_nodes"]
            for field in analysis_fields:
                if field in trace_analysis:
                    print(f"   ✅ Found {field} in trace_graph_analysis")
                else:
                    print(f"   ❌ Missing {field} in trace_graph_analysis")
                    return False
            
            # Print some key information
            if "service_graph" in trace_analysis:
                service_graph = trace_analysis["service_graph"]
                if isinstance(service_graph, dict):
                    if "root_service_name" in service_graph:
                        print(f"   Root Service: {service_graph['root_service_name']}")
                    if "total_services" in service_graph:
                        print(f"   Total Services: {service_graph['total_services']}")
                    if "error_rate" in service_graph:
                        print(f"   Error Rate: {service_graph['error_rate']}")
            
            if "relevant_nodes" in trace_analysis:
                relevant_nodes = trace_analysis["relevant_nodes"]
                if isinstance(relevant_nodes, list):
                    print(f"   Relevant Nodes Count: {len(relevant_nodes)}")
                    for i, node in enumerate(relevant_nodes[:3]):  # Show first 3 nodes
                        if isinstance(node, dict):
                            service_name = node.get("service_name", "Unknown")
                            reason = node.get("reason", "No reason provided")
                            print(f"     Node {i+1}: {service_name} - {reason}")
                else:
                    print("   ❌ relevant_nodes should be a list")
                    return False
        else:
            print("❌ trace_graph_analysis should be a dictionary")
            return False
        
        # Check raw_analysis
        if isinstance(response_data["raw_analysis"], str):
            print(f"   ✅ raw_analysis length: {len(response_data['raw_analysis'])} characters")
        else:
            print("❌ raw_analysis should be a string")
            return False
        
        # Check recommended_services
        if isinstance(response_data["recommended_services"], list):
            print(f"   ✅ recommended_services count: {len(response_data['recommended_services'])}")
            if response_data["recommended_services"]:
                print(f"     Services: {response_data['recommended_services']}")
        else:
            print("❌ recommended_services should be a list")
            return False
        
        print("✅ All required fields present and properly structured")
        return True

if __name__ == "__main__":
    test = TraceGraphAnalyzerTest()
    test.run_tests()
