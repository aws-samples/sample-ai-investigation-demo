"""Local test for ExecutorAgent to debug execution issues."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from aiops.orchestrator.executor_agent import ExecutorAgent
from aiops.utils.dynamodb_helper import InvestigationStore

def test_executor():
    """Test executor with a real investigation from DynamoDB."""
    
    # Get investigation ID from command line or use default
    investigation_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if not investigation_id:
        # List recent investigations
        store = InvestigationStore()
        print("No investigation_id provided. Checking DynamoDB for recent investigations...")
        # You can add code here to list recent investigations
        print("\nUsage: python test_executor_local.py <investigation_id>")
        return
    
    print(f"🧪 Testing ExecutorAgent with investigation: {investigation_id}")
    print("=" * 60)
    
    # Create executor
    executor = ExecutorAgent()
    
    # Execute workflow
    result = executor.execute_workflow(investigation_id)
    
    print("\n" + "=" * 60)
    print("📊 Result:")
    print(result)

if __name__ == "__main__":
    test_executor()
