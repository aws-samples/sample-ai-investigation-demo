"""MCP client with AWS SigV4 authentication for AgentCore Gateways."""

import boto3
from botocore.credentials import Credentials
from strands.tools.mcp.mcp_client import MCPClient
from .streamable_http_sigv4 import streamablehttp_client_with_sigv4

SERVICE = "bedrock-agentcore"

def create_gateway_mcp_client(gateway_url: str, region: str = None) -> MCPClient:
    """Create MCP client with SigV4 authentication for AgentCore Gateway.
    
    Args:
        gateway_url: Gateway URL
        region: AWS region (defaults to session region)
        
    Returns:
        MCPClient instance authenticated with IAM
    """
    session = boto3.Session()
    credentials = session.get_credentials()
    
    if region is None:
        region = session.region_name or "ap-southeast-1"
    
    def transport_factory():
        return streamablehttp_client_with_sigv4(
            url=gateway_url,
            credentials=Credentials(
                access_key=credentials.access_key,
                secret_key=credentials.secret_key,
                token=credentials.token
            ),
            service=SERVICE,
            region=region
        )
    
    return MCPClient(transport_factory)
