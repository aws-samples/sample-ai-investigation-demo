"""
Centralized logging configuration for AIOps Investigation Demo
Enhanced with trace-based logging support
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional


def setup_dual_logging(logger_name='aiops', log_file=None, log_level=logging.INFO, trace_id=None):
    """
    Set up logging to both console and file with consistent formatting
    Enhanced with trace-based directory support
    
    Args:
        logger_name (str): Name of the logger
        log_file (str): Path to log file. If None, uses default naming
        log_level: Logging level (default: INFO)
        trace_id (str): Optional trace ID for trace-specific logging
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create a logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    
    # Clear any existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatter with timestamp, logger name, level, and message
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler and set level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    logger.addHandler(console_handler)
    
    # Create file handler and set level
    if log_file is None:
        # Generate default log file name with timestamp
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = f'{logger_name}_{timestamp}.log'
    
    # Determine the log directory based on trace_id
    if trace_id:
        # Use trace-specific directory
        from trace_context import trace_context
        log_dir = trace_context.get_trace_directory(trace_id)
    else:
        # Try to get current trace ID
        try:
            from trace_context import get_current_trace_id, get_trace_directory
            current_trace_id = get_current_trace_id()
            if current_trace_id:
                log_dir = get_trace_directory(current_trace_id)
            else:
                # No trace context, use system directory
                log_dir = get_trace_directory(None)  # This will return system directory
        except ImportError:
            # Fallback to old behavior if trace_context not available
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            log_dir = os.path.join(project_root, 'logs', 'system')
            os.makedirs(log_dir, exist_ok=True)
    
    # Ensure the log file path is absolute
    if not os.path.dirname(log_file):
        log_file = os.path.join(log_dir, log_file)
    else:
        # If a directory is specified, ensure it exists
        specified_dir = os.path.dirname(log_file)
        os.makedirs(specified_dir, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)
    
    # Log the setup
    logger.info(f"Dual logging initialized - Console: {log_level}, File: {log_file}")
    
    return logger


def get_logger(name='aiops', trace_id=None):
    """
    Get an existing logger or create a new one with dual logging
    Enhanced with trace support
    
    Args:
        name (str): Logger name
        trace_id (str): Optional trace ID for trace-specific logging
        
    Returns:
        logging.Logger: Logger instance
    """
    logger = logging.getLogger(name)
    
    # If logger doesn't have handlers, set it up
    if not logger.handlers:
        return setup_dual_logging(name, trace_id=trace_id)
    
    return logger


def get_trace_aware_logger(name='aiops', trace_id=None):
    """
    Get a trace-aware logger that automatically uses current trace context
    
    Args:
        name (str): Logger name
        trace_id (str): Optional specific trace ID, uses current if None
        
    Returns:
        logging.Logger: Trace-aware logger instance
    """
    if trace_id is None:
        try:
            from trace_context import get_current_trace_id
            trace_id = get_current_trace_id()
        except ImportError:
            pass
    
    return setup_dual_logging(name, trace_id=trace_id)


# Pre-configured loggers for common use cases
def get_workflow_logger(trace_id=None):
    """Get logger for workflow operations"""
    return get_trace_aware_logger('aiops_workflow', trace_id)


def get_main_logger(trace_id=None):
    """Get logger for main application"""
    return get_trace_aware_logger('aiops_main', trace_id)


def get_streamlit_logger(trace_id=None):
    """Get logger for Streamlit app"""
    return get_trace_aware_logger('aiops_streamlit', trace_id)


def get_node_logger(node_name, trace_id=None):
    """Get logger for specific node operations"""
    return get_trace_aware_logger(f'aiops_node_{node_name}', trace_id)


def get_logs_directory():
    """
    Get the path to the logs directory
    
    Returns:
        str: Path to the logs directory
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    return os.path.join(project_root, 'logs')


def cleanup_old_logs(days_to_keep=7):
    """
    Clean up log files older than specified days
    Enhanced to handle trace directories
    
    Args:
        days_to_keep (int): Number of days to keep log files (default: 7)
    """
    import glob
    import time
    import shutil
    
    logs_dir = get_logs_directory()
    if not os.path.exists(logs_dir):
        return
    
    current_time = time.time()
    cutoff_time = current_time - (days_to_keep * 24 * 60 * 60)
    
    # Clean up trace directories
    for item in os.listdir(logs_dir):
        item_path = os.path.join(logs_dir, item)
        
        if os.path.isdir(item_path):
            # Check if it's a trace directory or system directory
            if item.startswith('trace-') or item == 'system':
                # Check the modification time of the directory
                dir_mtime = os.path.getmtime(item_path)
                if dir_mtime < cutoff_time:
                    try:
                        shutil.rmtree(item_path)
                        print(f"Removed old trace directory: {item_path}")
                    except OSError as e:
                        print(f"Error removing trace directory {item_path}: {e}")
        elif os.path.isfile(item_path) and item_path.endswith('.log'):
            # Handle any loose log files in the main logs directory
            file_age = current_time - os.path.getmtime(item_path)
            if file_age > (days_to_keep * 24 * 60 * 60):
                try:
                    os.remove(item_path)
                    print(f"Removed old log file: {item_path}")
                except OSError as e:
                    print(f"Error removing log file {item_path}: {e}")


def list_trace_sessions(days_back=7):
    """
    List recent trace sessions
    
    Args:
        days_back (int): Number of days back to look for traces
        
    Returns:
        list: List of trace information dictionaries
    """
    import json
    from datetime import datetime, timedelta
    
    logs_dir = get_logs_directory()
    if not os.path.exists(logs_dir):
        return []
    
    traces = []
    cutoff_date = datetime.now() - timedelta(days=days_back)
    
    for item in os.listdir(logs_dir):
        if item.startswith('trace-'):
            trace_dir = os.path.join(logs_dir, item)
            if os.path.isdir(trace_dir):
                metadata_file = os.path.join(trace_dir, 'trace_metadata.json')
                
                trace_info = {
                    'trace_id': item,
                    'directory': trace_dir,
                    'start_time': None,
                    'end_time': None,
                    'status': 'unknown'
                }
                
                # Try to read metadata
                if os.path.exists(metadata_file):
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            trace_info.update(metadata)
                    except Exception:
                        pass
                
                # Check if trace is within the time range
                if trace_info['start_time']:
                    try:
                        start_time = datetime.fromisoformat(trace_info['start_time'])
                        if start_time >= cutoff_date:
                            traces.append(trace_info)
                    except Exception:
                        # If we can't parse the date, include it anyway
                        traces.append(trace_info)
                else:
                    # No start time, check directory modification time
                    dir_mtime = datetime.fromtimestamp(os.path.getmtime(trace_dir))
                    if dir_mtime >= cutoff_date:
                        traces.append(trace_info)
    
    # Sort by start time (most recent first)
    traces.sort(key=lambda x: x.get('start_time', ''), reverse=True)
    return traces
