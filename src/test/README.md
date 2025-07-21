# Local Custom Tests

This directory contains custom test scripts for testing individual components of the AIOps investigation bot with specific scenarios.

## Test Directories

- **alarm_analyzer/**: Tests for the alarm_analyzer_node with different alarm scenarios
- **root_cause_analysis/**: Tests for the root_cause_analysis_node with different scenarios

## Running Tests

To run a test, navigate to the src directory and execute the test script:

```bash
cd /Users/yagrxu/me/collaborations/2025/aiops/ai-investigation-demo/src
./local/alarm_analyzer/test_custom_rds_alarm.py
```

## Creating New Test Directories

To create tests for a new component:

1. Create a new directory in the local folder named after the component
2. Add an `__init__.py` file to make it a proper package
3. Add a README.md file with documentation
4. Create test scripts following the established patterns

## Test Structure

Each test should follow this general structure:

```python
#!/usr/bin/env python3
"""
Custom test description
"""

import sys
import os
import json

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nodes.node_to_test import node_to_test
from langchain_core.messages import HumanMessage

# Custom test data
CUSTOM_DATA = """
Your test data here
"""

def test_function():
    """Test description"""
    # Initialize state
    initial_state = {
        "messages": [HumanMessage(content=CUSTOM_DATA)],
        "context": {}
    }
    
    # Call the node
    result = node_to_test(initial_state)
    
    # Print and verify results
    print("\nRESULT:")
    print(json.dumps(result, indent=2))
    
    return result

if __name__ == "__main__":
    test_function()
```
