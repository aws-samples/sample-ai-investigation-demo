#!/usr/bin/env python3
"""
Alarm analyzer node test using the simple base test framework
"""

import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_test import SimpleNodeTest
from nodes.alarm_analyzer_node import alarm_analyzer_node
from langchain_core.messages import HumanMessage

class AlarmAnalyzerTest(SimpleNodeTest):
    """Simple alarm analyzer node test"""
    
    def __init__(self):
        super().__init__(alarm_analyzer_node)
    
    def call_node(self, content):
        """Override to format content correctly for alarm analyzer node"""
        # Alarm analyzer expects messages with alarm details
        if isinstance(content, dict) and "alarm_details" in content:
            # Content has alarm details
            alarm_message = content["alarm_details"]
        elif isinstance(content, str):
            # Content is a string (alarm details)
            alarm_message = content
        else:
            # Use the entire content as alarm details
            alarm_message = str(content)
        
        state = {
            "messages": [HumanMessage(content=alarm_message)],
            "context": {}
        }
        return super().call_node(state)
    
    def validate_response(self, response):
        """Validate alarm analyzer response"""
        print(f"Response keys: {list(response.keys())}")
        
        # Check if we have context
        if "context" not in response:
            print("❌ No context in response")
            return False
        
        context = response["context"]
        
        # Check if we have alarm_analysis
        if "alarm_analysis" not in context:
            print("❌ No alarm_analysis in context")
            return False
        
        alarm_analysis = context["alarm_analysis"]
        print(f"Alarm analysis detail: \n {alarm_analysis}")
        
        if isinstance(alarm_analysis, dict):
            print("✅ Alarm analysis is a dictionary")
            
            # Check for expected alarm analysis fields
            expected_fields = ["identified_alarm_types", "severity", "extracted_info", "possible_causes"]
            found_fields = []
            
            for field in expected_fields:
                if field in alarm_analysis:
                    found_fields.append(field)
                    print(f"   ✅ Found field: {field}")
            
            if found_fields:
                print(f"✅ Found {len(found_fields)} expected fields: {found_fields}")
                
                # Print some key information
                if "identified_alarm_types" in alarm_analysis:
                    print(f"   Alarm Types: {alarm_analysis['identified_alarm_types']}")
                if "severity" in alarm_analysis:
                    print(f"   Severity: {alarm_analysis['severity']}")
                if "extracted_info" in alarm_analysis and isinstance(alarm_analysis["extracted_info"], dict):
                    extracted = alarm_analysis["extracted_info"]
                    if "alarm_name" in extracted:
                        print(f"   Alarm Name: {extracted['alarm_name']}")
                    if "region" in extracted:
                        print(f"   Region: {extracted['region']}")
                
                return True
            else:
                # If no expected fields, check if we have any meaningful data
                if alarm_analysis:
                    print(f"✅ Alarm analysis contains data: {list(alarm_analysis.keys())}")
                    return True
                else:
                    print("❌ Alarm analysis is empty")
                    return False
        
        elif isinstance(alarm_analysis, str):
            if alarm_analysis.strip():
                print("✅ Alarm analysis contains text data")
                return True
            else:
                print("❌ Alarm analysis is empty string")
                return False
        
        else:
            print(f"❌ Unexpected alarm analysis type: {type(alarm_analysis)}")
            return False

if __name__ == "__main__":
    test = AlarmAnalyzerTest()
    test.run_tests()
