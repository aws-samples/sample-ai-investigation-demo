from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage
import json
import os
import re
from logging_config import get_node_logger
from constants import AgentTypes
from util import get_bedrock_model, create_agent_executor, create_prompt_template
from test_data_decorator import export_test_data
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

class AIAgentNode:
    def __init__(self, config: Dict[str, Any], prompt_file: str, context_key: str, output_key: str = None, tools: Optional[List] = None):
        # Extract agent name from config or use a default
        self.agent_name = config.get("agent_name", "unknown_agent")
        
        # Load external configuration if model_id not provided
        if "model_id" not in config:
            from config_loader import get_node_config, get_unified_node_name
            try:
                external_config = get_node_config(self.agent_name)
                # Merge external config with provided config (provided config takes precedence)
                merged_config = external_config.copy()
                merged_config.update(config)
                config = merged_config
                
                # Update agent name with unified name for logging
                unified_name = get_unified_node_name(self.agent_name)
                self.logger = get_node_logger(f"aiops_node_{self.agent_name}")
                self.logger.info(f"Using external configuration for {unified_name} (model_id: {config['model_id']})")
            except Exception as e:
                self.logger = get_node_logger(f"aiops_node_{self.agent_name}")
                self.logger.warning(f"Could not load external config for {self.agent_name}: {e}")
                # Continue with provided config
        else:
            self.logger = get_node_logger(f"aiops_node_{self.agent_name}")
        
        self.prompt_template = self._load_prompt_template(prompt_file)
        self.context_key = context_key
        self.output_key = output_key or context_key
        self.tools = tools or []
        self.is_xml, self.model = get_bedrock_model(config["model_id"], config["max_tokens"])
        
        # If tools are provided, create agent executor
        if self.tools:
            if self.is_xml:
                # XML agents use the BASE_TEMPLATE_XML with tool descriptions
                self.logger.debug(f"Creating XML agent prompt template for {self.agent_name}")
                prompt = create_prompt_template(self.agent_name, self.prompt_template, AgentTypes.XML_AGENT)
                self.logger.debug(f"XML prompt template created successfully")
            else:
                # Function calling agents need escaped curly braces to avoid template variable conflicts
                # This allows JSON examples in prompts to be treated as literal text
                self.logger.debug(f"Creating function call agent prompt template for {self.agent_name}")
                escaped_prompt = self.prompt_template.replace("{", "{{").replace("}", "}}")
                prompt = ChatPromptTemplate.from_messages([
                    ("system", escaped_prompt),
                    ("human", "{input}"),
                    MessagesPlaceholder("agent_scratchpad"),
                ])
                self.logger.debug(f"Function call prompt template created successfully")

            self.agent_executor = create_agent_executor(
                self.model, 
                self.tools, 
                prompt,
                agent_type=AgentTypes.XML_AGENT if self.is_xml else AgentTypes.FUNCTION_CALL_AGENT
            )
            self.use_agent = True
            self.logger.info(f"Initialized {self.agent_name} with {len(self.tools)} tools using {'XML_AGENT' if self.is_xml else 'FUNCTION_CALL_AGENT'}")
        else:
            # No tools - direct model invocation
            self.agent_executor = None
            self.use_agent = False
            self.logger.info(f"Initialized {self.agent_name} without tools (direct model invocation)")

    def get_agent_info(self):
        """Get information about the agent configuration for debugging"""
        return {
            "agent_name": self.agent_name,
            "is_xml": self.is_xml,
            "use_agent": self.use_agent,
            "tools_count": len(self.tools),
            "context_key": self.context_key,
            "output_key": self.output_key
        }

    def _load_prompt_template(self, prompt_file: str) -> str:
        # Get the project root directory (two levels up from this file)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        prompt_path = os.path.join(project_root, "prompts", prompt_file)
        
        with open(prompt_path, 'r') as f:
            return f.read()

    def _process_response(self, response_content: str) -> Dict[str, Any]:
        json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decoding failed: {e}")
                return {"error": "Invalid JSON response", "content": response_content}
        return {"error": "No JSON found in response", "content": response_content}

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the AI agent with the given state
        
        Args:
            state: State dictionary containing context and messages
            
        Returns:
            Updated state with agent response
        """
        return self.__call__(state)

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"--- Running {self.agent_name} ---")
        self.logger.info(f"Agent config: {self.get_agent_info()}")
        
        input_data = state["context"].get(self.context_key)
        if not input_data:
            raise ValueError(f"Missing '{self.context_key}' in state context.")

        if self.use_agent:
            # Use agent executor for tool calling
            self.logger.info(f"Using agent executor with {len(self.tools)} tools")
            self.logger.debug(f"Input data preview: {str(input_data)[:200]}...")
            try:
                # For agent executor, pass the input data as formatted JSON string
                input_text = json.dumps(input_data, indent=2)
                self.logger.debug(f"Formatted input text length: {len(input_text)} characters")
                self.logger.debug(f"Agent executor type: {'XML_AGENT' if self.is_xml else 'FUNCTION_CALL_AGENT'}")
                
                agent_response = self.agent_executor.invoke({"input": input_text})
                
                # Extract the final answer from agent response
                if isinstance(agent_response, dict):
                    response_content = agent_response.get("output", "")
                    if not response_content:
                        response_content = str(agent_response)
                else:
                    response_content = str(agent_response)
                
                # For XML agents, extract content from <final_answer> tags if present
                if self.is_xml and "<final_answer>" in response_content:
                    import re
                    final_answer_match = re.search(r'<final_answer>(.*?)</final_answer>', response_content, re.DOTALL)
                    if final_answer_match:
                        response_content = final_answer_match.group(1).strip()
                        
            except Exception as e:
                import traceback
                error_details = {
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                    "traceback": traceback.format_exc()
                }
                self.logger.error(f"Agent executor failed: {error_details['exception_type']}: {error_details['exception_message']}")
                self.logger.error(f"Full traceback: {error_details['traceback']}")
                response_content = f"Agent execution failed: {error_details['exception_type']}: {error_details['exception_message']}"
        else:
            # Direct model invocation (original approach)
            self.logger.info("Using direct model invocation")
            prompt = self.prompt_template.replace('INPUT_DATA', json.dumps(input_data, indent=2))
            response = self.model.invoke(prompt)
            response_content = response.content

        processed_response = self._process_response(response_content)

        state["context"][self.output_key] = processed_response
        
        return {
            "messages": [AIMessage(content=json.dumps(processed_response, indent=2))],
            "context": state["context"]
        }