"""
Utility functions and shared components for AIOps agents
"""

import subprocess
import boto3
import json
import os
from typing import Optional
from langchain_core.tools import tool
from langchain_aws import ChatBedrock, ChatBedrockConverse
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, PromptTemplate
from langchain.agents import AgentExecutor, create_xml_agent

from constants import AgentTypes

# Add imports for the new agent types
try:
    from langchain.agents import create_tool_calling_agent, create_openai_functions_agent, create_structured_chat_agent
except ImportError as e:
    print(f"Some agent types may not be available: {e}")

# Import knowledge tools - commented out to avoid import error
# from knowledge import KNOWLEDGE_TOOLS

# Initialize Bedrock client, return the if type of XML
def get_bedrock_model(id=0, token_limit=150000):
    """Initialize and return a Bedrock model client
    
    Args:
        id: Model ID (0=Claude Haiku, 1=Claude Sonnet, 2=Claude Sonnet older, 3=Nova Micro, 4=Nova Premier)
        token_limit: Maximum tokens to generate
    """
    is_xml = True
    is_converse = False
    if id == 0:
        model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"
        region = "us-west-2"
    elif id == 1:
        model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
        region = "us-west-2"
    elif id == 2:
        model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
        region = "us-west-2"
    elif id == 3:
        # Nova Pro with cross-region inference
        model_id = "us.amazon.nova-pro-v1:0"
        region = "us-west-2"
        is_converse = True
        is_xml = False
    elif id == 4:
        # Nova Pro with cross-region inference
        model_id = "us.amazon.nova-premier-v1:0"
        region = "us-west-2"
        is_converse = True
        is_xml = False
    elif id == 5:
        # Claude 3.7 Sonnet with cross-region inference (alternative)
        model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
        region = "us-west-2"  # Cross-region inference supported
        is_converse = True
    else:
        model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"
        region = "us-west-2"
    return is_xml, create_langchain_model(model_id, region, token_limit, is_converse)

def create_langchain_model(model_id, region, token_limit, converse = False):
    """Create a LangChain model with the specified parameters"""
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=region,
    )
    
    if converse is True:
        # ChatBedrockConverse uses different parameter structure
        return ChatBedrockConverse(
            client=bedrock_runtime,
            model_id=model_id,
            max_tokens=token_limit,
            temperature=0.0,
        )
    else:
        # ChatBedrock uses model_kwargs
        model_kwargs = {
            "max_tokens": token_limit,
            "temperature": 0.0,
            "top_k": 250,
            "top_p": 1,
            "stop_sequences": ["\n\nHuman"],
        }
        return ChatBedrock(
            client=bedrock_runtime,
            model_id=model_id,
            model_kwargs=model_kwargs,
        )

def model_direct_invoke(input_text: str, model_id: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0", region: str = "us-east-1", max_tokens: int = 4000) -> str:
    """
    Direct invocation of Bedrock Claude model without LangChain wrapper
    
    Args:
        input_text: The input text/prompt to send to the model
        model_id: Bedrock model ID (default: Claude 3.7 Sonnet)
        region: AWS region (default: us-east-1)
        max_tokens: Maximum tokens to generate (default: 4000)
        
    Returns:
        str: Model response text
    """
    try:
        # Initialize Bedrock runtime client
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            region_name=region,
        )
        
        # Prepare the request body for Claude models
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": 0.0,
            "top_p": 1,
            "messages": [
                {
                    "role": "user",
                    "content": input_text
                }
            ]
        }
        
        # Make the API call
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        # Parse the response
        response_body = json.loads(response['body'].read())
        
        # Extract the text content
        if 'content' in response_body and len(response_body['content']) > 0:
            return response_body['content'][-1]['text']
        else:
            return "No response content received from model"
            
    except Exception as e:
        return f"Error invoking model: {str(e)}"

def model_direct_invoke_json(input_text: str, model_id: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0", region: str = "us-east-1", max_tokens: int = 4000) -> dict:
    """
    Direct invocation of Bedrock Claude model with JSON response parsing
    
    Args:
        input_text: The input text/prompt to send to the model
        model_id: Bedrock model ID (default: Claude 3.7 Sonnet)
        region: AWS region (default: us-east-1)
        max_tokens: Maximum tokens to generate (default: 4000)
        
    Returns:
        dict: Parsed JSON response or error dict
    """
    try:
        response_text = model_direct_invoke(input_text, model_id, region, max_tokens)
        
        # Try to parse as JSON
        if response_text.startswith("Error"):
            return {"error": response_text}
        
        # Look for JSON in the response (handle markdown code blocks)
        import re
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON without code blocks
            json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response_text
        
        return json.loads(json_str)
        
    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse JSON response: {str(e)}",
            "raw_response": response_text
        }
    except Exception as e:
        return {"error": f"Error in JSON invocation: {str(e)}"}

def model_direct_invoke_quick(prompt: str, max_tokens: int = 1000) -> str:
    """
    Quick direct model invocation with default settings
    
    Args:
        prompt: The prompt to send to the model
        max_tokens: Maximum tokens (default: 1000)
        
    Returns:
        str: Model response
    """
    return model_direct_invoke(
        input_text=prompt,
        model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        region="us-east-1",
        max_tokens=max_tokens
    )

@tool("get_lambda_function_logs")
def get_lambda_function_logs(function_name: str, start_time: Optional[str] = None, end_time: Optional[str] = None, trace_id: Optional[str] = None) -> str:
    """Get logs for a specific AWS Lambda function within an optional time range.
    
    Args:
        function_name (str): The name of the Lambda function.
        start_time (Optional[str]): Start time in ISO 8601 format (e.g., '2023-10-01T00:00:00Z').
        end_time (Optional[str]): End time in ISO 8601 format (e.g., '2023-10-01T23:59:59Z').
        
    Returns:
        str: Logs for the specified Lambda function.
    """
    logs_client = boto3.client('logs')
    
    log_group_name = f"/aws/lambda/{function_name}"
    
    query = f"fields @timestamp, @message | sort @timestamp desc | limit 20"
    
    if start_time and end_time:
        start_query_response = logs_client.start_query(
            logGroupName=log_group_name,
            startTime=int(pd.Timestamp(start_time).timestamp()),
            endTime=int(pd.Timestamp(end_time).timestamp()),
            queryString=query,
        )
    else:
        start_query_response = logs_client.start_query(
            logGroupName=log_group_name,
            startTime=int(pd.Timestamp.now().timestamp()) - 3600,  # Default to last hour
            endTime=int(pd.Timestamp.now().timestamp()),
            queryString=query,
        )
    
    query_id = start_query_response['queryId']
    
    # Wait for the query to complete
    response = None
    while response is None or response['status'] == 'Running':
        print("Waiting for query to complete...")
        response = logs_client.get_query_results(queryId=query_id)
    
    return json.dumps(response['results'], indent=2)

@tool
def execute_aws_cli(command: str) -> str:
    """Execute an AWS CLI command locally and return the output."""
    # Validate input
    if not command.startswith("aws "):
        return "Error: Invalid AWS CLI command. The command must start with 'aws'."

    try:
        # Execute the AWS CLI command locally using subprocess
        safe_command = command
        # result = subprocess.run(safe_command, check=True, capture_output=True, text=True)
        # return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: Command execution failed. Exit code: {e.returncode}, Error: {e.stderr.strip()}"
    except Exception as e:
        return f"Unexpected error executing AWS CLI command: {str(e)}"

# Define base prompt template
# Load base templates from prompts folder
def load_base_template(template_name: str) -> str:
    """Load base template from prompts folder"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    template_path = os.path.join(project_root, "prompts", template_name)
    
    with open(template_path, 'r') as f:
        return f.read()

# Load base templates
BASE_TEMPLATE_XML = load_base_template("base_template_xml.txt")
BASE_TEMPLATE_FUNCTION_CALL = load_base_template("base_template_function_call.txt")

# Create prompt templates for each agent
def create_prompt_template(role, role_specific_instructions, agent_type=AgentTypes.XML_AGENT):
    """Create a prompt template for an agent with specific role and instructions"""
    
    # Choose the appropriate base template based on agent type
    if agent_type == AgentTypes.XML_AGENT:
        base_template = BASE_TEMPLATE_XML
        input_vars = ["agent_scratchpad", "input", "tools", "role", "role_specific_instructions"]
    else:  # FUNCTION_CALL_AGENT
        base_template = BASE_TEMPLATE_FUNCTION_CALL
        input_vars = ["input", "role", "role_specific_instructions"]
    
    prompt_template = PromptTemplate(
        input_variables=input_vars,
        template=base_template
    )
    
    human_message_prompt = HumanMessagePromptTemplate(
        prompt=prompt_template
    )
    
    # For XML agents, include tools in input variables
    if agent_type == AgentTypes.XML_AGENT:
        chat_input_vars = ["agent_scratchpad", "input", "tools"]
    else:
        chat_input_vars = ["input"]
    
    return ChatPromptTemplate(
        input_variables=chat_input_vars,
        partial_variables={
            "role": role,
            "role_specific_instructions": role_specific_instructions
        },
        messages=[human_message_prompt]
    )

# Common tools list
COMMON_TOOLS = [execute_aws_cli]# + KNOWLEDGE_TOOLS

# Create a generic agent executor
def create_agent_executor(model, tools, prompt, agent_type=AgentTypes.XML_AGENT, verbose=True):
    """Create an agent executor with the given model, tools, and prompt
    
    Args:
        model: The LLM model to use
        tools: List of tools available to the agent
        prompt: The prompt template
        agent_type: Type of agent ("xml", "calling", "structured_chat")
        verbose: Whether to enable verbose logging
    """
    try:
        if agent_type == AgentTypes.XML_AGENT:
            agent = create_xml_agent(model, tools, prompt)
        elif agent_type == AgentTypes.FUNCTION_CALL_AGENT:
            # Real implementation for function calling agents
            try:
                from langchain.agents import create_tool_calling_agent
                agent = create_tool_calling_agent(model, tools, prompt)
            except Exception as e:
                # Fallback to OpenAI functions agent
                print(f"Error creating {agent_type} agent: {e}")
                from langchain.agents import create_openai_functions_agent
                agent = create_openai_functions_agent(model, tools, prompt)
        elif agent_type == AgentTypes.STRUCTURED_CHAT_AGENT:
            # Real implementation for structured chat agents
            from langchain.agents import create_structured_chat_agent
            agent = create_structured_chat_agent(model, tools, prompt)
        else:
            # Default to XML for unknown types
            print(f"Warning: Unknown agent_type '{agent_type}', defaulting to 'xml'")
            agent = create_xml_agent(model, tools, prompt)
        
        return AgentExecutor(agent=agent, tools=tools, return_intermediate_steps=True, verbose=verbose)
        
    except Exception as e:
        print(f"Error creating {agent_type} agent: {e}")
        print("Falling back to XML agent...")
        agent = create_xml_agent(model, tools, prompt)
        return AgentExecutor(agent=agent, tools=tools, return_intermediate_steps=True, verbose=verbose)
def invoke_agent_with_retry(agent_executor, input_data, logger, max_retries=3):
    """
    Invoke an agent executor with retry logic for throttling
    
    Args:
        agent_executor: The LangChain agent executor
        input_data: Input data for the agent
        logger: Logger instance for error reporting
        max_retries: Maximum number of retry attempts
        
    Returns:
        Agent execution result or None if all retries failed
    """
    import time
    import random
    from botocore.exceptions import ClientError
    
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            result = agent_executor.invoke(input_data)
            return result
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"Throttling detected, retrying in {delay:.2f} seconds (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Agent failed after {max_retries} attempts due to throttling: {str(e)}")
                    raise
            else:
                logger.error(f"AWS API error in agent: {str(e)}")
                raise
                
        except Exception as e:
            logger.error(f"Agent execution failed: {str(e)}")
            raise
    
    return None
