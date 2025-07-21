#!/usr/bin/env python3
"""
Simple decision node test
"""

import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_test import SimpleNodeTest
from nodes.decision_node import decision_node
from langchain_core.messages import HumanMessage

class DecisionTest(SimpleNodeTest):
    """Simple decision node test"""
    
    def __init__(self):
        super().__init__(decision_node)
    
    def call_node(self, content):
        """Override to format content correctly for decision node"""
        # Decision node expects messages and context
        state = {
            "messages": [HumanMessage(content="Please analyze this alarm")],
            "context": {
                "alarm_analysis": content  # Put the loaded content as alarm_analysis
            }
        }
        return super().call_node(state)
    
    def validate_response(self, response):
        """Validate decision node response"""
        print(f"Response keys: {list(response.keys())}")
        
        # Check if we have context and initial_decision
        if "context" not in response:
            print("❌ No context in response")
            return False
        
        if "initial_decision" not in response["context"]:
            print("❌ No initial_decision in context")
            return False
        
        decision = response["context"]["initial_decision"]
        print(f"Decision: {decision}")
        
        # Check required fields
        required_fields = ["alert_type", "resource_type", "severity", "recommended_path"]
        for field in required_fields:
            if field not in decision:
                print(f"❌ Missing field: {field}")
                return False
        
        print("✅ All required fields present")
        print(f"   Alert Type: {decision['alert_type']}")
        print(f"   Resource Type: {decision['resource_type']}")
        print(f"   Severity: {decision['severity']}")
        print(f"   Recommended Path: {decision['recommended_path']}")
        
        return True

if __name__ == "__main__":
    test = DecisionTest()
    test.run_tests()
