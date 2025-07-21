"""
Test Data Exporter - Captures real workflow execution data for testing

This module provides functionality to export real workflow execution data
to be used as test samples. It's controlled by the EXPORT_TEST_DATA environment variable.
"""

import os
import json
import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import hashlib

class TestDataExporter:
    """Exports workflow execution data for testing purposes"""
    
    def __init__(self):
        self.enabled = os.getenv('EXPORT_TEST_DATA', 'false').lower() == 'true'
        self.export_dir = Path(__file__).parent / "test"
        self.run_id = self._generate_run_id()
        self.exported_nodes = set()
        
    def _generate_run_id(self) -> str:
        """Generate a unique run ID for this execution"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"run_{timestamp}"
    
    def _sanitize_data(self, data: Any) -> Any:
        """Sanitize data by removing sensitive information and making it JSON serializable"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Skip sensitive keys
                if key.lower() in ['password', 'secret', 'token', 'key', 'credential']:
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self._sanitize_data(value)
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif hasattr(data, 'content'):  # LangChain message objects
            return {
                'type': type(data).__name__,
                'content': str(data.content)
            }
        elif hasattr(data, '__dict__'):  # Other objects with attributes
            return {
                'type': type(data).__name__,
                'data': self._sanitize_data(data.__dict__)
            }
        else:
            # Handle non-JSON serializable types
            try:
                json.dumps(data)
                return data
            except (TypeError, ValueError):
                return str(data)
    
    def _extract_node_content(self, node_name: str, input_state: Dict[str, Any]):
        """Extract meaningful content from node input based on node type"""
        
        # For alarm_analyzer, extract the alarm text from input messages
        if node_name == "alarm_analyzer":
            # Try to get the message content (which contains the alarm text)
            if "messages" in input_state and input_state["messages"]:
                message = input_state["messages"][-1]  # Get the last message
                if hasattr(message, 'content'):
                    return message.content  # Return the raw alarm text
                elif isinstance(message, dict) and 'content' in message:
                    return message['content']  # Return the raw alarm text
                elif isinstance(message, str):
                    return message  # Return the string directly
            
            # Fallback: return the whole input_state
            return self._sanitize_data(input_state)
        
        # For other nodes, return the full input_state for now
        return self._sanitize_data(input_state)
    
    def export_node_data(self, node_name: str, input_state: Dict[str, Any], 
                        output_state: Dict[str, Any], isJson: bool = True, execution_time: Optional[float] = None):
        """
        Export node execution data for testing
        
        Args:
            node_name: Name of the node (e.g., 'alarm_analyzer', 'logs_collector')
            input_state: The input state passed to the node
            output_state: The output state returned by the node
            execution_time: Optional execution time in seconds
        """
        if not self.enabled:
            return
            
        try:
            # Create directory structure
            node_test_dir = self.export_dir / node_name
            samples_dir = node_test_dir / "samples"
            samples_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate sample filename
            ext = "json" if isJson else "txt"
            sample_filename = f"sample_{self.run_id}_{len(self.exported_nodes):03d}.{ext}"
            sample_path = samples_dir / sample_filename
            
            # Prepare export data - extract meaningful content based on node type
            export_data = self._extract_node_content(node_name, input_state)
            
            # Write to file
            with open(sample_path, 'w', encoding='utf-8') as f:
                if isJson:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                else:
                    # For text files, convert to string if needed
                    content = export_data if isinstance(export_data, str) else json.dumps(export_data, indent=2)
                    f.write(content)
            
            # Track exported nodes
            self.exported_nodes.add(node_name)
            
            print(f"✅ Exported test data for {node_name} to {sample_path}")
            
            # Also create a summary file
            self._update_export_summary(node_name, sample_filename)
            
        except Exception as e:
            print(f"❌ Failed to export test data for {node_name}: {e}")
    
    def _update_export_summary(self, node_name: str, sample_filename: str):
        """Update the export summary file"""
        summary_path = self.export_dir / f"export_summary_{self.run_id}.json"
        
        # Load existing summary or create new
        if summary_path.exists():
            with open(summary_path, 'r') as f:
                summary = json.load(f)
        else:
            summary = {
                "run_id": self.run_id,
                "export_timestamp": datetime.datetime.now().isoformat(),
                "exported_nodes": {}
            }
        
        # Update summary
        summary["exported_nodes"][node_name] = {
            "sample_file": sample_filename,
            "export_time": datetime.datetime.now().isoformat()
        }
        
        # Write summary
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

# Global exporter instance
_exporter = TestDataExporter()

def export_node_execution(node_name: str, input_state: Dict[str, Any], 
                         output_state: Dict[str, Any], isJson: bool = True, execution_time: Optional[float] = None):
    """
    Convenience function to export node execution data
    
    Usage:
        from test_data_exporter import export_node_execution
        
        def my_node(state):
            # ... node logic ...
            result = {...}
            
            # Export for testing (only if EXPORT_TEST_DATA=true)
            export_node_execution("my_node", state, result, execution_time)
            
            return result
    """
    _exporter.export_node_data(node_name, input_state, output_state, isJson, execution_time)

def is_export_enabled() -> bool:
    """Check if test data export is enabled"""
    return _exporter.enabled
