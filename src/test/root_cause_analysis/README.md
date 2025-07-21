# Root Cause Analysis Custom Tests

This directory contains custom test scripts specifically for testing the root_cause_analysis_node with different scenarios.

## Available Tests

- **test_custom_root_cause.py**: Test for the root_cause_analysis_node with an API Gateway error scenario

## Running Tests

To run a test, navigate to the src directory and execute the test script:

```bash
cd /Users/yagrxu/me/collaborations/2025/aiops/ai-investigation-demo/src
./local/root_cause_analysis/test_custom_root_cause.py
```

## Adding New Root Cause Analysis Tests

To create a new root cause analysis test:

1. Create a new Python file in this directory
2. Import the root_cause_analysis_node
3. Define your custom scenario with appropriate context data
4. Create a test function that initializes the state and calls the node
5. Print and verify the results
6. Make the script executable with `chmod +x`

## Test Structure

Each test should follow this general structure:

```python
#!/usr/bin/env python3
"""
Custom test for root_cause_analysis_node with a specific scenario
"""

import sys
import os
import json

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nodes.root_cause_analysis_node import root_cause_analysis_node
from langchain_core.messages import HumanMessage

def test_custom_scenario():
    """Test description"""
    # Create sample context data
    sample_context = {
        "alarm_analysis": { ... },
        "resource_info": { ... },
        "cloudops_data": { ... },
        "trace_analysis": { ... }
    }
    
    # Initialize state
    initial_state = {
        "messages": [HumanMessage(content="Your test message")],
        "context": sample_context
    }
    
    # Call the node
    result = root_cause_analysis_node(initial_state)
    
    # Print and verify results
    print("\nRESULT:")
    print(json.dumps(result, indent=2))
    
    return result

if __name__ == "__main__":
    test_custom_scenario()
```
