#!/usr/bin/env python3
"""
Test script for the root_cause_analysis_node with file input
"""

import sys
import os
import json
import argparse

# Add the src directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nodes.root_cause_analysis_node import root_cause_analysis_node
from langchain_core.messages import HumanMessage

# Import constants
from constants import ContextKeys, AnalysisKeys

def verify_root_cause_output(result, test_name):
    """Comprehensive verification of root_cause_analysis output"""
    print(f"\n🔍 VERIFICATION FOR {test_name}:")
    
    verification_results = {
        "message_structure": False,
        "context_structure": False,
        "root_cause_data": False,
        "analysis_quality": False,
        "content_quality": False
    }
    
    # 1. Verify message structure
    if result.get('messages') and len(result['messages']) > 0:
        message_content = result['messages'][0].content
        if message_content and len(message_content) > 100:
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
    
    # 3. Verify root_cause data presence
    if 'root_cause' in context:
        root_cause = context['root_cause']
        verification_results["root_cause_data"] = True
        print("✅ Root cause data: Present")
        print(f"   - Root cause keys: {list(root_cause.keys())}")
        
        # 4. Verify analysis quality
        required_fields = ['identified_cause', 'confidence_score', 'recommended_actions']
        found_fields = [field for field in required_fields if field in root_cause]
        if len(found_fields) >= 2:  # At least 2 required fields
            verification_results["analysis_quality"] = True
            print(f"✅ Analysis quality: Good ({found_fields})")
            
            # Check confidence score
            confidence = root_cause.get('confidence_score', 0)
            print(f"   - Confidence score: {confidence}")
            
            # Check identified cause
            cause = root_cause.get('identified_cause', 'Unknown')
            print(f"   - Identified cause: {cause}")
        else:
            print(f"❌ Analysis quality: Poor ({found_fields})")
    else:
        print("❌ Root cause data: Missing")
    
    # 5. Verify content quality
    message_length = len(result['messages'][0].content) if result.get('messages') else 0
    if message_length > 300:  # Substantial content for root cause analysis
        verification_results["content_quality"] = True
        print(f"✅ Content quality: Good ({message_length} characters)")
    else:
        print(f"❌ Content quality: Poor ({message_length} characters)")
    
    # Overall score
    passed_checks = sum(verification_results.values())
    total_checks = len(verification_results)
    score = (passed_checks / total_checks) * 100
    
    print(f"\n📊 VERIFICATION SCORE: {passed_checks}/{total_checks} ({score:.1f}%)")
    
    return score >= 60  # 60% threshold for pass

def load_test_data_from_file(file_path):
    """Load test data from a JSON file"""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading test data from file: {e}")
        return None

def test_root_cause_with_file(file_path):
    """Test root_cause_analysis with input from file"""
    print(f"\n{'='*80}")
    print(f"TESTING ROOT CAUSE ANALYSIS WITH FILE: {file_path}")
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
    
    # Convert message content to string if it's a dict
    if isinstance(message_content, dict):
        message_content_str = json.dumps(message_content)
    else:
        message_content_str = str(message_content)
    
    print(f"✅ Extracted message content ({len(message_content_str)} characters)")
    print(f"✅ Extracted context with keys: {list(context_data.keys())}")
    
    # Show data source availability
    data_sources = []
    if context_data.get(ContextKeys.ALARM_ANALYSIS):
        data_sources.append(ContextKeys.ALARM_ANALYSIS)
    if context_data.get('resource_info'):
        data_sources.append('resource_info')
    if context_data.get('logs_data'):
        data_sources.append('logs_data')
    if context_data.get('cloudtrail_data'):
        data_sources.append('cloudtrail_data')
    if context_data.get(ContextKeys.TRACE_ANALYSIS):
        data_sources.append(ContextKeys.TRACE_ANALYSIS)
    
    print(f"✅ Available data sources: {data_sources} ({len(data_sources)} total)")
    
    # Create initial state following the correct structure
    initial_state = {
        "messages": [HumanMessage(content=message_content_str)],
        "context": context_data
    }
    
    # Call the root_cause_analysis_node
    print("\nCalling root_cause_analysis_node...")
    result = root_cause_analysis_node(initial_state)
    
    # Print basic results
    print("\nBASIC RESULTS:")
    print(f"- Message length: {len(result['messages'][0].content)} characters")
    print(f"- Context keys: {list(result['context'].keys())}")
    
    # Show root cause summary
    if result.get('context', {}).get('root_cause'):
        root_cause = result['context']['root_cause']
        print(f"- Identified cause: {root_cause.get('identified_cause', 'Unknown')}")
        print(f"- Confidence score: {root_cause.get('confidence_score', 0)}")
        print(f"- Recommended actions: {len(root_cause.get('recommended_actions', []))}")
    
    # Show sample output
    if result.get('messages'):
        sample_content = result['messages'][0].content[:400] + "..."
        print(f"- Sample output: {sample_content}")
    
    # Comprehensive verification
    test_name = os.path.basename(file_path).replace('.json', '').upper()
    return verify_root_cause_output(result, test_name)

def main():
    """Main function to parse arguments and run the test"""
    parser = argparse.ArgumentParser(description='Test the root_cause_analysis_node with input from a file')
    parser.add_argument('input_file', help='Path to the JSON file containing the test data')
    
    args = parser.parse_args()
    
    success = test_root_cause_with_file(args.input_file)
    
    if success:
        print("\n🎉 Root Cause Analysis test PASSED!")
        return 0
    else:
        print("\n❌ Root Cause Analysis test FAILED!")
        return 1

if __name__ == "__main__":
    exit(main())
