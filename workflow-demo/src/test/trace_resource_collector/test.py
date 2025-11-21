#!/usr/bin/env python3
"""
Test script for trace_resource_collector_node

This script tests the trace resource collector node with sample data to ensure it works correctly.
"""

import sys
import os
import json
from pathlib import Path

# Add the src directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from nodes.trace_resource_collector_node import trace_resource_collector_node
from langchain_core.messages import HumanMessage

def test_trace_resource_collector_with_file(file_path):
    """Test the trace resource collector node with data from a file"""
    
    print(f"\n{'='*80}")
    print(f"TESTING TRACE RESOURCE COLLECTOR WITH FILE: {file_path}")
    print(f"{'='*80}")
    
    # Load test data from file
    try:
        with open(file_path, 'r') as f:
            test_data = json.load(f)
        print(f"✅ Loaded test data from file ({len(json.dumps(test_data))} characters)")
    except Exception as e:
        print(f"❌ Error loading test data: {e}")
        return
    
    # Extract message content and context
    message_content = test_data.get("messages", [])[0].get("content", {})
    context = test_data.get("context", {})
    
    print(f"✅ Extracted message content ({len(message_content)} characters)")
    print(f"✅ Extracted context with keys: {list(context.keys())}")
    
    # Create test state
    test_state = {
        "messages": [HumanMessage(content=json.dumps(message_content))],
        "context": context
    }
    
    print(f"\nCalling trace_resource_collector_node...")
    
    try:
        # Call the node
        result = trace_resource_collector_node(test_state)
        
        print(f"✅ Node executed successfully")
        print(f"✅ Result keys: {list(result.keys())}")
        
        # Check the result structure
        if "messages" in result and result["messages"]:
            response_content = result["messages"][0].content
            print(f"✅ Response content length: {len(response_content)} characters")
            
            # Try to parse the response as JSON
            try:
                response_json = json.loads(response_content)
                print(f"✅ Response is valid JSON")
                print(f"✅ Response keys: {list(response_json.keys())}")
                
                # Check for expected structure
                if "resource_collection" in response_json:
                    resource_collection = response_json["resource_collection"]
                    print(f"✅ Resource collection found with keys: {list(resource_collection.keys())}")
                    
                    # Check resource types
                    resource_types = ["ec2_resources", "lambda_resources", "s3_resources", "rds_resources", "apigateway_resources"]
                    for resource_type in resource_types:
                        if resource_type in resource_collection:
                            count = len(resource_collection[resource_type]) if isinstance(resource_collection[resource_type], list) else 0
                            print(f"   - {resource_type}: {count} items")
                
                if "raw_analysis" in response_json:
                    analysis_length = len(response_json["raw_analysis"])
                    print(f"✅ Raw analysis found ({analysis_length} characters)")
                
                if "recommendations" in response_json:
                    rec_count = len(response_json["recommendations"]) if isinstance(response_json["recommendations"], list) else 0
                    print(f"✅ Recommendations found ({rec_count} items)")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Response is not valid JSON: {e}")
                print(f"Response preview: {response_content[:200]}...")
        
        if "context" in result:
            context_keys = list(result["context"].keys())
            print(f"✅ Updated context with keys: {context_keys}")
            
            if "resource_collection" in result["context"]:
                print(f"✅ Resource collection added to context")
        
        print(f"\n🎉 TRACE RESOURCE COLLECTOR TEST COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"❌ Error during node execution: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main test function"""
    
    if len(sys.argv) != 2:
        print("Usage: python test.py <test_file.json>")
        print("\nAvailable test files:")
        test_dir = Path(__file__).parent / "samples"
        if test_dir.exists():
            for file in test_dir.glob("*.json"):
                print(f"  - {file.name}")
        sys.exit(1)
    
    test_file = sys.argv[1]
    
    # If it's just a filename, look in the samples directory
    if not os.path.exists(test_file):
        samples_dir = Path(__file__).parent / "samples"
        test_file = samples_dir / test_file
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        sys.exit(1)
    
    test_trace_resource_collector_with_file(test_file)

if __name__ == "__main__":
    main()
