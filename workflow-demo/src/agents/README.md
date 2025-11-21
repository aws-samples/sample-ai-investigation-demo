# AIOps Investigation Agents

This directory contains the agent implementations for the AIOps investigation bot. These agents are specialized components that perform specific tasks in the investigation workflow.

## Available Agents

- **agent.py**: Base agent class that defines common functionality
- **domain_bot_agent.py**: Agent for domain-specific analysis
- **incident_processor_agent.py**: Agent for processing and summarizing incidents
- **resource_collector_agent.py**: Agent for collecting resource information

## Agent Structure

Each agent follows a similar structure:

1. **Initialization**: Set up the agent with necessary configuration
2. **Process Method**: Main method for processing input and generating output
3. **Helper Methods**: Additional methods for specific tasks

## Using Agents

Agents can be used directly or through the LangGraph workflow:

```python
from agents.domain_bot_agent import DomainBotAgent

# Create an agent instance
agent = DomainBotAgent()

# Process input
result = agent.process(input_data)
```

## Creating New Agents

To create a new agent:

1. Create a new Python file in the agents directory
2. Import the base Agent class
3. Implement the required methods
4. Add the agent to the __init__.py file

Example:

```python
from agents.agent import Agent

class NewAgent(Agent):
    def __init__(self):
        super().__init__("New Agent")
        
    def process(self, input_data):
        # Process the input data
        result = self._process_data(input_data)
        return result
        
    def _process_data(self, data):
        # Helper method for processing data
        return processed_data
```
