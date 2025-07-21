"""
Test Data Loader - Loads exported test data for use in unit tests
"""

import json
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional

class TestDataLoader:
    """Loads exported test data for unit testing"""
    
    def __init__(self, test_dir: Optional[Path] = None):
        if test_dir is None:
            self.test_dir = Path(__file__).parent / "test"
        else:
            self.test_dir = Path(test_dir)
    
    def load_samples_for_node(self, node_name: str) -> List[Dict[str, Any]]:
        """
        Load all test samples for a specific node
        
        Args:
            node_name: Name of the node (e.g., 'alarm_analyzer')
            
        Returns:
            List of test sample dictionaries
        """
        samples_dir = self.test_dir / node_name / "samples"
        if not samples_dir.exists():
            return []
        
        samples = []
        sample_files = glob.glob(str(samples_dir / "*.json"))
        
        for sample_file in sorted(sample_files):
            try:
                with open(sample_file, 'r', encoding='utf-8') as f:
                    sample_data = json.load(f)
                    samples.append(sample_data)
            except Exception as e:
                print(f"Warning: Failed to load sample {sample_file}: {e}")
        
        return samples
    
    def load_latest_sample_for_node(self, node_name: str) -> Optional[Dict[str, Any]]:
        """
        Load the most recent test sample for a node
        
        Args:
            node_name: Name of the node
            
        Returns:
            Latest test sample or None if no samples exist
        """
        samples = self.load_samples_for_node(node_name)
        if not samples:
            return None
        
        # Sort by timestamp and return the latest
        samples.sort(key=lambda x: x.get('metadata', {}).get('timestamp', ''))
        return samples[-1]
    
    def get_input_state(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        """Extract input state from a test sample"""
        return sample.get('input_state', {})
    
    def get_expected_output(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        """Extract expected output from a test sample"""
        return sample.get('expected_output', {})
    
    def list_available_nodes(self) -> List[str]:
        """List all nodes that have exported test data"""
        if not self.test_dir.exists():
            return []
        
        nodes = []
        for item in self.test_dir.iterdir():
            if item.is_dir() and (item / "samples").exists():
                nodes.append(item.name)
        
        return sorted(nodes)
    
    def get_sample_count(self, node_name: str) -> int:
        """Get the number of available samples for a node"""
        return len(self.load_samples_for_node(node_name))

# Convenience functions for easy use in tests
def load_test_samples(node_name: str) -> List[Dict[str, Any]]:
    """Load all test samples for a node"""
    loader = TestDataLoader()
    return loader.load_samples_for_node(node_name)

def load_latest_test_sample(node_name: str) -> Optional[Dict[str, Any]]:
    """Load the latest test sample for a node"""
    loader = TestDataLoader()
    return loader.load_latest_sample_for_node(node_name)
