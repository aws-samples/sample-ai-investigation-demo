"""Tool loader for loading MCP tools from gateways."""

from typing import List
from .mcp_client import create_gateway_mcp_client
from .gateway_config import get_gateways_for_agent, get_gateway_url

def load_tools_for_agent(agent_name: str, region: str = None) -> List:
    """Load all tools for an agent from configured gateways.
    
    Args:
        agent_name: Name of the agent (e.g., "LogsAgent")
        region: AWS region (defaults to session region)
        
    Returns:
        List of tools from all configured gateways
    """
    tools = []
    gateway_names = get_gateways_for_agent(agent_name)
    
    for gateway_name in gateway_names:
        gateway_url = get_gateway_url(gateway_name)
        if not gateway_url:
            raise ValueError(f"Gateway URL not configured for {gateway_name}")
        
        mcp_client = create_gateway_mcp_client(gateway_url, region)
        
        with mcp_client:
            # List all tools from gateway
            gateway_tools = []
            pagination_token = None
            
            while True:
                result = mcp_client.list_tools_sync(pagination_token=pagination_token)
                gateway_tools.extend(result)
                
                if result.pagination_token is None:
                    break
                pagination_token = result.pagination_token
            
            tools.extend(gateway_tools)
    
    return tools
