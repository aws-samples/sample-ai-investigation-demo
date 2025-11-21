# AIOps demo

This is an AIOps projectin python, which leverages LLM Agents techniques to support incident investigation.

The demo is a 3 layers architecture, WebUI -> LangGraph (workflow of LLM agents) -> tooling function calls. 

- Web UI is currently using streamlit to receive alarm description and present AI workflow progress.
- LangGraph uses multiple agent nodes to collect and analyze operation data.
- tooling functions provide convenient access to the data in operation platform.

examplpe of the calling sequence.
Alarm Analysis → Decision Node → Trace Finder Node → Downstream Nodes

The working directory structure:

/prompts:
In prompts folder it should contain the prompts of all agent nodes.

/design: design documents including architecture, components and descriptions 

/src: src is the entry for code.

/src/nodes: has all node implementation and all nodes extends from a base node called 'ai_agent_node'

/src/agents: is a legacy folder, in the old implementation node calls agent, but in the latest one, agent is also implemented in node python file.

/src/tools: is used for tooling function call.

