#!/usr/bin/env python3
"""
Simple base test class for AIOps node testing
"""

import sys
import os
import json
import argparse
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SimpleNodeTest(ABC):
    """
    Simple base class for node tests
    """
    
    def __init__(self, node_function: Callable):
        """
        Initialize the test
        
        Args:
            node_function: The node function to test
        """
        self.node_function = node_function
    
    def load_file(self, file_path: str):
        """Load content from file (supports both JSON and text files)"""
        if file_path.endswith('.json'):
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            # For text files, return the content as a string
            with open(file_path, 'r') as f:
                return f.read().strip()
    
    def call_node(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Call the node with the content"""
        return self.node_function(content)
    
    @abstractmethod
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate the response - to be implemented by each test"""
        pass
    
    def test_file(self, file_path: str) -> bool:
        """Test with a single file"""
        print(f"Testing with file: {file_path}")
        
        # Load content
        content = self.load_file(file_path)
        
        # Call node
        response = self.call_node(content)
        
        # Validate response
        is_valid = self.validate_response(response)
        
        print(f"Test result: {'PASS' if is_valid else 'FAIL'}")
        return is_valid
    
    def run_tests(self):
        """Run tests based on command line arguments"""
        parser = argparse.ArgumentParser(description='Run node tests')
        parser.add_argument('--file', help='Test with specific file')
        parser.add_argument('--all', action='store_true', help='Test with all files in samples directory')
        
        args = parser.parse_args()
        
        if args.file:
            self.test_file(args.file)
        elif args.all:
            # Test all files in samples directory
            samples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'samples')
            if os.path.exists(samples_dir):
                for file_name in os.listdir(samples_dir):
                    if file_name.endswith(('.json', '.txt')):
                        file_path = os.path.join(samples_dir, file_name)
                        self.test_file(file_path)
        else:
            print("Please specify --file or --all")
