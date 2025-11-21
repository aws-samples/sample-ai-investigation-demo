"""Tool integration layer for MCP gateways."""

from .mcp_client import create_gateway_mcp_client
from .gateway_config import (
    AGENT_GATEWAY_CONFIG,
    get_gateways_for_agent,
    get_agent_description,
    get_gateway_url
)
from .tool_loader import load_tools_for_agent

__all__ = [
    "create_gateway_mcp_client",
    "AGENT_GATEWAY_CONFIG",
    "get_gateways_for_agent",
    "get_agent_description",
    "get_gateway_url",
    "load_tools_for_agent"
]
