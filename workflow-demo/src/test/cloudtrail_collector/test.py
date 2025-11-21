#!/usr/bin/env python3
"""
CloudTrail collector node test using the simple base test framework
"""

import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_test import SimpleNodeTest
from nodes.cloudtrail_collector_node import cloudtrail_collector_node
from langchain_core.messages import HumanMessage

class CloudTrailCollectorTest(SimpleNodeTest):
    """Simple CloudTrail collector node test"""
    
    def __init__(self):
        super().__init__(cloudtrail_collector_node)
    
    def call_node(self, content):
        """Override to format content correctly for cloudtrail collector node"""
        # CloudTrail collector expects messages and context with log analysis
        state = {
            "messages": [HumanMessage(content="Please collect CloudTrail data for this incident")],
            "context": content  # Use the entire loaded content as context
        }
        return super().call_node(state)
    
    def validate_response(self, response):
        """Validate CloudTrail collector response"""
        print(f"Response keys: {list(response.keys())}")
        
        # Check if we have context
        if "context" not in response:
            print("❌ No context in response")
            return False
        
        context = response["context"]
        
        # Check if we have cloudtrail_analysis
        if "cloudtrail_analysis" not in context:
            print("❌ No cloudtrail_analysis in context")
            return False
        
        cloudtrail_analysis = context["cloudtrail_analysis"]
        print(f"CloudTrail analysis type: {type(cloudtrail_analysis)}")
        
        if isinstance(cloudtrail_analysis, dict):
            print("✅ CloudTrail analysis is a dictionary")
            
            # Check for common CloudTrail analysis fields
            expected_fields = ["events", "analysis", "timeline"]
            found_fields = []
            
            for field in expected_fields:
                if field in cloudtrail_analysis:
                    found_fields.append(field)
                    print(f"   ✅ Found field: {field}")
            
            if found_fields:
                print(f"✅ Found {len(found_fields)} expected fields: {found_fields}")
                return True
            else:
                # If no expected fields, check if we have any meaningful data
                if cloudtrail_analysis:
                    print(f"✅ CloudTrail analysis contains data: {list(cloudtrail_analysis.keys())}")
                    return True
                else:
                    print("❌ CloudTrail analysis is empty")
                    return False
        
        elif isinstance(cloudtrail_analysis, str):
            if cloudtrail_analysis.strip():
                print("✅ CloudTrail analysis contains text data")
                return True
            else:
                print("❌ CloudTrail analysis is empty string")
                return False
        
        else:
            print(f"❌ Unexpected CloudTrail analysis type: {type(cloudtrail_analysis)}")
            return False

if __name__ == "__main__":
    test = CloudTrailCollectorTest()
    test.run_tests()
