#!/usr/bin/env python3
"""
Test script for the incident_processor_node with file input
"""

import sys
import os
import json
import argparse

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nodes.incident_processor_node import incident_processor_node
from langchain_core.messages import HumanMessage

# Import constants
from constants import ContextKeys, AnalysisKeys

def verify_incident_output(result, test_name):
    """Comprehensive verification of incident_processor output"""
    print(f"\n🔍 VERIFICATION FOR {test_name}:")
    
    verification_results = {
        "message_structure": False,
        "context_structure": False,
        "incident_info": False,
        "report_completeness": False,
        "actionable_content": False
    }
    
    # 1. Verify message structure
    if result.get('messages') and len(result['messages']) > 0:
        message_content = result['messages'][0].content
        if message_content and len(message_content) > 200:
            verification_results["message_structure"] = True
            print("✅ Message structure: Valid")
        else:
            print("❌ Message structure: Invalid or too short")
    else:
        print("❌ Message structure: Missing")
    
    # 2. Verify context structure
    context = result.get('context', {})
    if context and isinstance(context, dict):
        verification_results["context_structure"] = True
        print("✅ Context structure: Valid")
        print(f"   - Context keys: {list(context.keys())}")
    else:
        print("❌ Context structure: Invalid")
    
    # 3. Verify incident_info presence
    if 'incident_info' in context:
        incident_info = context['incident_info']
        verification_results["incident_info"] = True
        print("✅ Incident info: Present")
        print(f"   - Incident info keys: {list(incident_info.keys())}")
        
        # 4. Verify report completeness
        if incident_info or any(key in context for key in ['root_cause', ContextKeys.ALARM_ANALYSIS]):
            verification_results["report_completeness"] = True
            print(f"✅ Report completeness: Good")
        else:
            print(f"❌ Report completeness: Poor")
    else:
        print("❌ Incident info: Missing")
    
    # 5. Verify actionable content
    message_content = result['messages'][0].content if result.get('messages') else ""
    actionable_keywords = ['recommend', 'action', 'step', 'fix', 'resolve', 'prevent']
    found_keywords = [kw for kw in actionable_keywords if kw in message_content.lower()]
    if len(found_keywords) >= 2:
        verification_results["actionable_content"] = True
        print(f"✅ Actionable content: Present ({found_keywords})")
    else:
        print(f"❌ Actionable content: Limited ({found_keywords})")
    
    # Overall score
    passed_checks = sum(verification_results.values())
    total_checks = len(verification_results)
    score = (passed_checks / total_checks) * 100
    
    print(f"\n📊 VERIFICATION SCORE: {passed_checks}/{total_checks} ({score:.1f}%)")
    
    return score >= 60  # 60% threshold for pass

def load_test_data_from_file(file_path):
    """Load input data from a JSON file"""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading input from file: {e}")
        return None

def test_incident_processor_with_file(file_path):
    """Test incident_processor with input from file"""
    print(f"\n{'='*80}")
    print(f"TESTING INCIDENT PROCESSOR WITH FILE: {file_path}")
    print(f"{'='*80}")
    
    # Load test data from file
    test_data = load_test_data_from_file(file_path)
    if not test_data:
        print("❌ Failed to load test data from file")
        return False
    
    print(f"✅ Loaded test data from file ({len(json.dumps(test_data))} characters)")
    
    # Extract message content and context from test data following correct structure
    messages_data = test_data.get('messages', [])
    context_data = test_data.get('context', {})
    
    if not messages_data or len(messages_data) == 0:
        print("❌ No messages found in test data")
        return False
    
    # Get the content from the first message
    message_content = messages_data[0].get('content', {})
    
    # Convert message content to JSON string if it's a dict
    if isinstance(message_content, dict):
        message_content_str = json.dumps(message_content)
    else:
        message_content_str = str(message_content)
    
    print(f"✅ Extracted message content ({len(message_content_str)} characters)")
    print(f"✅ Extracted context with keys: {list(context_data.keys())}")
    
    # Create initial state following the correct structure
    initial_state = {
        "messages": [HumanMessage(content=message_content_str)],
        "context": context_data
    }
    
    # Call the incident_processor_node
    print("\nCalling incident_processor_node...")
    result = incident_processor_node(initial_state)
    
    # Print basic results
    print("\nBASIC RESULTS:")
    print(f"- Message length: {len(result['messages'][0].content)} characters")
    print(f"- Context keys: {list(result['context'].keys())}")
    
    # Show sample of the incident report
    if result.get('messages'):
        sample_content = result['messages'][0].content[:300] + "..."
        print(f"- Sample content: {sample_content}")
    
    # Comprehensive verification
    test_name = os.path.basename(file_path).replace('.json', '').upper()
    return verify_incident_output(result, test_name)

def main():
    """Main function to parse arguments and run the test"""
    parser = argparse.ArgumentParser(description='Test the incident_processor_node with input from a file')
    parser.add_argument('input_file', help='Path to the JSON file containing the input data')
    
    args = parser.parse_args()
    
    success = test_incident_processor_with_file(args.input_file)
    
    if success:
        print("\n🎉 Incident Processor test PASSED!")
        return 0
    else:
        print("\n❌ Incident Processor test FAILED!")
        return 1

if __name__ == "__main__":
    exit(main())
