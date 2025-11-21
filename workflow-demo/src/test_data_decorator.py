import time
import functools
from typing import Callable, Dict, Any
from test_data_exporter import export_node_execution, is_export_enabled

def export_test_data(node_name: str, isJson: bool = True):
    """
    Decorator to automatically export test data from node functions
    
    Usage:
        @export_test_data("alarm_analyzer")
        def alarm_analyzer_node(state):
            # ... node logic ...
            return result
    
    Args:
        node_name: Name of the node for test data export
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Dict[str, Any]:
            # The state is expected to be the first argument
            state = args[0] if args else kwargs.get('state')
            if not state:
                raise ValueError("The decorated function must have a 'state' argument.")

            if not is_export_enabled():
                # If export is disabled, just run the function normally
                return func(*args, **kwargs)
            
            # Record start time
            start_time = time.time()
            
            try:
                # Execute the node function
                result = func(*args, **kwargs)
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Export the test data
                export_node_execution(node_name, state, result, isJson, execution_time)
                
                return result
                
            except Exception as e:
                # Even if the node fails, we might want to export the failure case
                execution_time = time.time() - start_time
                error_result = {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "execution_failed": True
                }
                
                export_node_execution(f"{node_name}_error", state, error_result, isJson, execution_time)
                
                # Re-raise the original exception
                raise
        
        return wrapper
    return decorator