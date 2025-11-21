"""Base agent class and communication infrastructure using Strands framework"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from ..models.enums import AgentType
from ..models.data_models import Investigation

try:
    from strands import Agent, tool
except ImportError:
    # Fallback for development/testing without Strands
    class Agent:
        def __init__(self, system_prompt: str, tools: List = None, **kwargs):
            self.system_prompt = system_prompt
            self.tools = tools or []
            
        def __call__(self, message: str, **kwargs) -> str:
            return f"Mock response to: {message}"
    
    def tool(func):
        return func


@dataclass
class AgentState:
    """State of an individual agent"""
    agent_id: str
    agent_type: AgentType
    current_task: Optional[str] = None
    load_level: float = 0.0
    last_activity: datetime = field(default_factory=datetime.now)
    capabilities: List[str] = field(default_factory=list)
    is_active: bool = True
    
    def __post_init__(self):
        """Validate agent state after initialization"""
        if not 0.0 <= self.load_level <= 1.0:
            raise ValueError("Load level must be between 0.0 and 1.0")


@dataclass
class SystemState:
    """Shared state across all agents"""
    active_investigations: Dict[str, Investigation] = field(default_factory=dict)
    agent_states: Dict[str, AgentState] = field(default_factory=dict)
    workflow_templates: Dict[str, Any] = field(default_factory=dict)
    confidence_thresholds: Dict[str, float] = field(default_factory=dict)
    
    def add_investigation(self, investigation: Investigation) -> None:
        """Add investigation to active investigations"""
        self.active_investigations[investigation.investigation_id] = investigation
    
    def get_investigation(self, investigation_id: str) -> Optional[Investigation]:
        """Get investigation by ID"""
        return self.active_investigations.get(investigation_id)
    
    def update_investigation(self, investigation: Investigation) -> None:
        """Update investigation in shared state"""
        investigation.updated_at = datetime.now()
        self.active_investigations[investigation.investigation_id] = investigation
    
    def register_agent(self, agent_state: AgentState) -> None:
        """Register agent in system state"""
        self.agent_states[agent_state.agent_id] = agent_state
    
    def get_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Get agent state by ID"""
        return self.agent_states.get(agent_id)


class BaseStrandsAgent(ABC):
    """Base class for Strands-based agents"""
    
    def __init__(self, agent_id: str, agent_type: AgentType, system_state: SystemState):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.system_state = system_state
        self.capabilities: List[str] = []
        self._strands_agent: Optional[Agent] = None
        
        # Register agent in system state
        agent_state = AgentState(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=self.capabilities
        )
        self.system_state.register_agent(agent_state)
    
    @property
    def strands_agent(self) -> Agent:
        """Get or create the Strands Agent instance"""
        if self._strands_agent is None:
            model_config = self._load_model_config()
            model = self._create_model_from_config(model_config)
            
            self._strands_agent = Agent(
                system_prompt=self.get_system_prompt(),
                tools=self.get_tools(),
                model=model
            )
        return self._strands_agent
    
    def _load_model_config(self) -> Dict[str, Any]:
        """Load model configuration from file"""
        import json
        import os
        
        # Try multiple config file locations
        config_paths = [
            "config/model_config.json",
            "model_config.json",
            os.path.expanduser("~/.aiops/model_config.json"),
            "/etc/aiops/model_config.json"
        ]
        
        for config_path in config_paths:
            try:
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        print(f"Loaded model config from: {config_path}")
                        return config
            except Exception as e:
                print(f"Failed to load config from {config_path}: {e}")
                continue
        
        # Fallback to default configuration
        print("Using default model configuration")
        return {
            "default_model": {
                "provider": "bedrock",
                "model_id": "apac.amazon.nova-pro-v1:0",
                "region": "ap-southeast-1",
                "cross_region_inference_enabled": True
            },
            "agent_models": {},
            "fallback_models": [
                "apac.amazon.nova-pro-v1:0",
                "anthropic.claude-3-haiku-20240307-v1:0"
            ]
        }
    
    def _create_model_from_config(self, config: Dict[str, Any]):
        """Create model instance from configuration"""
        # Get agent-specific config or fall back to default
        agent_models = config.get("agent_models", {})
        agent_config = agent_models.get(self.agent_id, config.get("default_model", {}))
        
        provider = agent_config.get("provider", "bedrock")
        
        if provider == "bedrock":
            from strands.models import BedrockModel
            
            model_kwargs = {
                "model_id": agent_config.get("model_id", "apac.amazon.nova-pro-v1:0"),
                "region": agent_config.get("region", "ap-southeast-1")
            }
            
            # Add optional parameters if present
            if "cross_region_inference_enabled" in agent_config:
                model_kwargs["cross_region_inference_enabled"] = agent_config["cross_region_inference_enabled"]
            
            if "endpoint_url" in agent_config:
                model_kwargs["endpoint_url"] = agent_config["endpoint_url"]
            
            if "max_tokens" in agent_config:
                model_kwargs["max_tokens"] = agent_config["max_tokens"]
                
            if "temperature" in agent_config:
                model_kwargs["temperature"] = agent_config["temperature"]
            
            print(f"Creating {provider} model for {self.agent_id}: {model_kwargs['model_id']}")
            return BedrockModel(**model_kwargs)
        
        else:
            # Fallback to default Strands model
            print(f"Unknown provider '{provider}', using default model")
            return None
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass
    
    @abstractmethod
    def get_tools(self) -> List:
        """Get the tools for this agent"""
        pass
    
    def process_request(self, request: str, **kwargs) -> str:
        """Process a request using the Strands agent"""
        self.update_state(current_task=request[:50] + "..." if len(request) > 50 else request)
        
        try:
            # Pass system state through invocation_state
            invocation_state = kwargs.get('invocation_state', {})
            invocation_state.update({
                'agent_id': self.agent_id,
                'system_state': self.system_state,
                'agent_capabilities': self.capabilities
            })
            
            response = self.strands_agent(request, invocation_state=invocation_state, **kwargs)
            
            # Extract text from response if it's a complex object
            if hasattr(response, 'text'):
                return response.text
            elif isinstance(response, str):
                return response
            else:
                return str(response)
                
        finally:
            self.update_state(current_task=None)
    
    def update_state(self, current_task: Optional[str] = None, load_level: Optional[float] = None) -> None:
        """Update agent state"""
        agent_state = self.system_state.get_agent_state(self.agent_id)
        if agent_state:
            if current_task is not None:
                agent_state.current_task = current_task
            if load_level is not None:
                agent_state.load_level = load_level
            agent_state.last_activity = datetime.now()
    
    def get_investigation_context(self, investigation_id: str) -> Optional[Investigation]:
        """Get investigation context from shared state"""
        return self.system_state.get_investigation(investigation_id)
    
    def update_investigation_context(self, investigation: Investigation) -> None:
        """Update investigation context in shared state"""
        self.system_state.update_investigation(investigation)
    
    def is_agent_available(self, agent_id: str) -> bool:
        """Check if another agent is available"""
        agent_state = self.system_state.get_agent_state(agent_id)
        return agent_state is not None and agent_state.is_active
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities - to be implemented by subclasses"""
        pass