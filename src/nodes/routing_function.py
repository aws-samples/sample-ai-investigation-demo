"""
Routing function for AIOps workflow
"""

from typing import Dict, Any
import sys
import os
import json

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def routing_function(state: Dict[str, Any]) -> str:
    """
    Function to decide which path to take based on the initial decision.
    
    Args:
        state: Current state containing the conversation and messages
        
    Returns:
        String indicating which path to take: "trace" or "resource"
    """
    # Safely parse message content with error handling
    message = {}
    if state.get('messages') and len(state.get('messages', [])) > 0:
        message_content = state.get('messages', [])[-1].content
        if message_content and message_content.strip():
            try:
                message = json.loads(message_content)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse message content as JSON in routing_function: {e}")
                # Fallback to empty dict
                message = {}
        else:
            print("Warning: Message content is empty or None in routing_function")
    else:
        print("Warning: No messages found in state in routing_function")
    
    decision = message.get('decision', {}) if isinstance(message, dict) else {}
    
    # Get the recommended path from the initial decision
    recommended_path = decision.get("recommended_path", "resource")
    
    # Handle different path recommendations
    if recommended_path == "trace":
        return "trace"
    elif recommended_path == "hybrid":
        # For hybrid approach, prefer trace path for better analysis
        return "trace"
    else:
        # Default to resource path for "resource" or unknown paths
        return "resource"
