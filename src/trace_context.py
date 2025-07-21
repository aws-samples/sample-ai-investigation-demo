"""
Trace Context Manager for AIOps Investigation Demo
Manages UUID-based trace IDs and trace-specific logging directories
"""

import uuid
import os
import threading
from typing import Optional
from datetime import datetime

class TraceContext:
    """
    Thread-safe trace context manager for handling trace IDs and directories
    """
    
    def __init__(self):
        self._local = threading.local()
        self._base_logs_dir = None
    
    def generate_trace_id(self) -> str:
        """
        Generate a new UUID-based trace ID
        
        Returns:
            str: Formatted trace ID (e.g., "trace-550e8400-e29b-41d4-a716-446655440000")
        """
        trace_uuid = str(uuid.uuid4())
        return f"trace-{trace_uuid}"
    
    def set_current_trace_id(self, trace_id: str) -> None:
        """
        Set the current trace ID for this thread
        
        Args:
            trace_id (str): The trace ID to set
        """
        self._local.trace_id = trace_id
    
    def get_current_trace_id(self) -> Optional[str]:
        """
        Get the current trace ID for this thread
        
        Returns:
            Optional[str]: Current trace ID or None if not set
        """
        return getattr(self._local, 'trace_id', None)
    
    def clear_trace_id(self) -> None:
        """
        Clear the current trace ID for this thread
        """
        if hasattr(self._local, 'trace_id'):
            delattr(self._local, 'trace_id')
    
    def get_logs_base_directory(self) -> str:
        """
        Get the base logs directory path
        
        Returns:
            str: Path to the base logs directory
        """
        if self._base_logs_dir is None:
            # Get the project root directory (parent of src)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            self._base_logs_dir = os.path.join(project_root, 'logs')
        
        return self._base_logs_dir
    
    def create_trace_directory(self, trace_id: str) -> str:
        """
        Create a directory for the given trace ID
        
        Args:
            trace_id (str): The trace ID to create directory for
            
        Returns:
            str: Path to the created trace directory
        """
        base_logs_dir = self.get_logs_base_directory()
        trace_dir = os.path.join(base_logs_dir, trace_id)
        
        # Create the directory if it doesn't exist
        os.makedirs(trace_dir, exist_ok=True)
        
        return trace_dir
    
    def get_trace_directory(self, trace_id: Optional[str] = None) -> str:
        """
        Get the trace directory path for the given or current trace ID
        
        Args:
            trace_id (Optional[str]): Specific trace ID, or None to use current
            
        Returns:
            str: Path to the trace directory
        """
        if trace_id is None:
            trace_id = self.get_current_trace_id()
        
        if trace_id is None:
            # No trace ID, return system directory
            base_logs_dir = self.get_logs_base_directory()
            system_dir = os.path.join(base_logs_dir, 'system')
            os.makedirs(system_dir, exist_ok=True)
            return system_dir
        
        return self.create_trace_directory(trace_id)
    
    def start_trace_session(self, trace_id: Optional[str] = None) -> str:
        """
        Start a new trace session
        
        Args:
            trace_id (Optional[str]): Specific trace ID, or None to generate new one
            
        Returns:
            str: The trace ID for this session
        """
        if trace_id is None:
            trace_id = self.generate_trace_id()
        
        self.set_current_trace_id(trace_id)
        trace_dir = self.create_trace_directory(trace_id)
        
        # Create a trace metadata file
        self._create_trace_metadata(trace_id, trace_dir)
        
        return trace_id
    
    def end_trace_session(self) -> Optional[str]:
        """
        End the current trace session
        
        Returns:
            Optional[str]: The trace ID that was ended, or None if no active session
        """
        trace_id = self.get_current_trace_id()
        if trace_id:
            # Update trace metadata with end time
            trace_dir = self.get_trace_directory(trace_id)
            self._update_trace_metadata(trace_id, trace_dir, end_time=datetime.now())
            self.clear_trace_id()
        
        return trace_id
    
    def _create_trace_metadata(self, trace_id: str, trace_dir: str) -> None:
        """
        Create metadata file for the trace
        
        Args:
            trace_id (str): The trace ID
            trace_dir (str): The trace directory path
        """
        metadata = {
            "trace_id": trace_id,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "status": "active"
        }
        
        metadata_file = os.path.join(trace_dir, "trace_metadata.json")
        try:
            import json
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception:
            # Silently fail if we can't write metadata
            pass
    
    def _update_trace_metadata(self, trace_id: str, trace_dir: str, end_time: datetime) -> None:
        """
        Update trace metadata with end time
        
        Args:
            trace_id (str): The trace ID
            trace_dir (str): The trace directory path
            end_time (datetime): The end time
        """
        metadata_file = os.path.join(trace_dir, "trace_metadata.json")
        try:
            import json
            # Read existing metadata
            metadata = {}
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            
            # Update with end time
            metadata.update({
                "end_time": end_time.isoformat(),
                "status": "completed"
            })
            
            # Write back
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception:
            # Silently fail if we can't update metadata
            pass


# Global trace context instance
trace_context = TraceContext()


# Convenience functions for easy access
def generate_trace_id() -> str:
    """Generate a new trace ID"""
    return trace_context.generate_trace_id()


def start_trace_session(trace_id: Optional[str] = None) -> str:
    """Start a new trace session"""
    return trace_context.start_trace_session(trace_id)


def end_trace_session() -> Optional[str]:
    """End the current trace session"""
    return trace_context.end_trace_session()


def get_current_trace_id() -> Optional[str]:
    """Get the current trace ID"""
    return trace_context.get_current_trace_id()


def get_trace_directory(trace_id: Optional[str] = None) -> str:
    """Get the trace directory path"""
    return trace_context.get_trace_directory(trace_id)
