#!/usr/bin/env python3
"""
Test script for the logs_collector_node with file input
"""

import sys
import os
import json
import argparse

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nodes.logs_collector_node import logs_collector_node
from langchain_core.messages import HumanMessage

def verify_logs_output(result, test_name):
    """Comprehensive verification of logs_collector output"""
    print(f"\n🔍 VERIFICATION FOR {test_name}:")
    
    verification_results = {
        "message_structure": False,
        "context_structure": False,
        "log_data": False,
        "data_categories": False,
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
    
    # 3. Verify log_data presence
    message_content = json.loads(message_content)
    if 'log_data' in message_content['log_analysis']:
        log_data = message_content['log_analysis']['log_data']
        verification_results["log_data"] = True
        print("✅ Logs data: Present")
        print(f"   - Logs data keys: {list(log_data[0].keys())}")
        
        # 4. Verify data categories
        expected_categories = ['logs', 'summary']
        found_categories = [cat for cat in expected_categories if cat in log_data[0]]
        if len(found_categories) >= 1:  # At least 1 category
            verification_results["data_categories"] = True
            print(f"✅ Data categories: {found_categories}")
        else:
            print(f"❌ Data categories: Insufficient ({found_categories})")
    else:
        print("❌ Logs data: Missing")
    
    # 5. Verify content quality
    message_length = len(result['messages'][0].content) if result.get('messages') else 0
    if message_length > 200:  # Substantial content
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

def test_logs_with_file(file_path):
    """Test logs_collector with input from file"""
    print(f"\n{'='*80}")
    print(f"TESTING LOGS COLLECTOR WITH FILE: {file_path}")
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
    
    # Call the logs_collector_node
    print("\nCalling logs_collector_node...")
    result = logs_collector_node(initial_state)
    
    # Print basic results
    print("\nBASIC RESULTS:")
    print(f"- Message length: {len(result['messages'][0].content)} characters")
    print(f"- Context keys: {list(result['context'].keys())}")
    
    # Show sample output
    if result.get('messages'):
        sample_content = result['messages'][0].content
        print(f"- Sample output: {sample_content}")
    
    # Comprehensive verification
    test_name = os.path.basename(file_path).replace('.json', '').upper()
    return verify_logs_output(result, test_name)

def main():
    """Main function to parse arguments and run the test"""
    parser = argparse.ArgumentParser(description='Test the logs_collector_node with input from a file')
    parser.add_argument('input_file', help='Path to the JSON file containing the test data')
    
    args = parser.parse_args()
    
    success = test_logs_with_file(args.input_file)
    
    if success:
        print("\n🎉 Logs Collector test PASSED!")
        return 0
    else:
        print("\n❌ Logs Collector test FAILED!")
        return 1

if __name__ == "__main__":
    exit(main())
