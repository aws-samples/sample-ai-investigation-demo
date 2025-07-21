# Node Migration Task List

## Overview
Migration from using separate agent classes to extending directly from `ai_agent_node.py`. This eliminates the dependency on the `/agents` folder and consolidates the agent logic within each node.

## Migration Status

### ✅ Completed
- [x] `alarm_analyzer_node.py` - Already migrated
- [x] `cloudtrail_collector_node.py` - Already migrated
- [x] `decision_node.py` - ✅ **JUST COMPLETED** - Migrated to use AIAgentNode with decision_prompt.txt

### 🔄 Pending Migration (9 nodes)

#### High Priority (Core workflow nodes)

1. **trace_finder_node.py**
   - Current: Uses `TraceFinderAgent` from `agents.trace_finder_agent`
   - Action: Migrate to extend from `AIAgentNode`
   - Impact: High - core trace discovery functionality

2. **incident_processor_node.py**
   - Current: Uses `IncidentProcessorAgent` from `agents.incident_processor_agent`
   - Action: Migrate to extend from `AIAgentNode`
   - Impact: High - processes incident data

#### Medium Priority (Analysis nodes)
3. **root_cause_analysis_node.py**
   - Current: Uses `RootCauseAnalysisAgent` from `agents.root_cause_analysis_agent`
   - Action: Migrate to extend from `AIAgentNode`
   - Impact: Medium - final analysis step

4. **trace_details_analyzer_node.py**
   - Current: Uses `TraceDetailsAnalyzerAgent` from `agents.trace_details_analyzer_agent`
   - Action: Migrate to extend from `AIAgentNode`
   - Impact: Medium - trace analysis

5. **trace_graph_analyzer_node.py**
   - Current: Uses `TraceGraphAnalyzerAgent` from `agents.trace_graph_analyzer_agent`
   - Action: Migrate to extend from `AIAgentNode`
   - Impact: Medium - graph analysis

#### Lower Priority (Data collection nodes)
6. **logs_collector_node.py**
   - Current: Uses `LogsCollectorAgent` from `agents.logs_collector_agent`
   - Action: Migrate to extend from `AIAgentNode`
   - Impact: Low - data collection

7. **resource_collector_node.py**
   - Current: Uses `ResourceCollectorAgent` from `agents.resource_collector_agent`
   - Action: Migrate to extend from `AIAgentNode`
   - Impact: Low - data collection

8. **trace_resource_collector_node.py**
   - Current: Uses `TraceResourceCollectorAgent` from `agents.trace_resource_collector_agent`
   - Action: Migrate to extend from `AIAgentNode`
   - Impact: Low - data collection

9. **domain_bot_node.py**
    - Current: Uses `DomainBotAgent` from `agents.domain_bot_agent`
    - Action: Migrate to extend from `AIAgentNode`
    - Impact: Low - specialized domain knowledge

## Migration Pattern

Based on the successfully migrated nodes (`alarm_analyzer_node.py` and `cloudtrail_collector_node.py`), follow this pattern:

### Before (Old Pattern):
```python
from agents.some_agent import SomeAgent

def some_node(state: Dict[str, Any]):
    agent = SomeAgent()
    result = agent.process(state)
    return result
```

### After (New Pattern):
```python
from nodes.ai_agent_node import AIAgentNode, run_ai_agent_node

def some_node(state: Dict[str, Any]):
    return run_ai_agent_node(
        state=state,
        node_name="some_node",
        system_prompt="...",  # Move from agent to here
        tools=COMMON_TOOLS,   # Or specific tools
        context_keys=[...]    # Required context
    )
```

## Migration Steps for Each Node

1. **Remove agent import**
   - Delete `from agents.xxx_agent import XxxAgent`

2. **Add ai_agent_node import**
   - Add `from nodes.ai_agent_node import AIAgentNode, run_ai_agent_node`

3. **Extract system prompt**
   - Copy system prompt from agent class to node function
   - Place in `run_ai_agent_node` call

4. **Extract tools configuration**
   - Copy tools list from agent to node
   - Use `COMMON_TOOLS` or specific tool list

5. **Update function logic**
   - Replace agent instantiation and method calls
   - Use `run_ai_agent_node` with appropriate parameters

6. **Test the migration**
   - Ensure node still functions correctly
   - Verify prompt and tool behavior

## Post-Migration Cleanup

After all nodes are migrated:

1. **Remove agents folder**
   - Delete `/src/agents/` directory entirely
   - Update any remaining imports if found

2. **Update documentation**
   - Update README.md to reflect new architecture
   - Remove references to agents folder

3. **Clean up imports**
   - Remove any unused agent imports from other files
   - Update `__init__.py` files if needed

## Testing Strategy

- Test each migrated node individually
- Run full workflow to ensure integration works
- Compare outputs before/after migration
- Verify all prompts and tools are working correctly

## Notes

- The `routing_function.py` doesn't use agents, so no migration needed
- `ai_agent_node.py` is the base class, no migration needed
- `__init__.py` may need updates after migration
