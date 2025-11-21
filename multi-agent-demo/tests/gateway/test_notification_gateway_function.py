from strands.models import BedrockModel
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client 
from botocore.credentials import Credentials
from streamable_http_sigv4 import streamablehttp_client_with_sigv4
import logging
import os

SERVICE = "bedrock-agentcore"

logging.getLogger("strands").setLevel(logging.INFO)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s", 
    handlers=[logging.StreamHandler()]
)

model = BedrockModel(model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0")

def create_streamable_http_transport_sigv4(mcp_url: str, key: str, secret: str, serviceName: str, awsRegion: str):
    iamcredentials = Credentials(access_key=key, secret_key=secret)
    return streamablehttp_client_with_sigv4(
        url=mcp_url,
        credentials=iamcredentials,
        service=serviceName,
        region=awsRegion,
    )

def run_agent_test(mcp_url: str, key: str, secret: str, serviceName: str, awsRegion: str):
    mcp_client = MCPClient(lambda: create_streamable_http_transport_sigv4(mcp_url, key, secret, serviceName, awsRegion))

    with mcp_client:
        # Load tools
        tools = []
        pagination_token = None
        while True:
            result = mcp_client.list_tools_sync(pagination_token=pagination_token)
            tools.extend(result)
            if result.pagination_token is None:
                break
            pagination_token = result.pagination_token
        
        print(f"✅ Loaded {len(tools)} tools: {[tool.tool_name for tool in tools]}")
        
        # Create agent with tools
        agent = Agent(
            model=model,
            tools=tools,
            system_prompt="You are NotificationAgent. Use available tools directly. Be concise."
        )
        
        # Execute agent
        print("\n▶️  Executing agent...")
        response = agent("Send notification: instance id i-12345678 has CPU utilization over 90% now!")
        print(f"\n✅ Agent response: {response.message if hasattr(response, 'message') else str(response)}")

access = os.getenv('AWS_ACCESS_KEY_ID')
secret = os.getenv('AWS_SECRET_ACCESS_KEY')
gateway_url = os.getenv('NOTIFICATION_GATEWAY_URL')

run_agent_test(gateway_url, access, secret, SERVICE, os.environ['AWS_DEFAULT_REGION'])
