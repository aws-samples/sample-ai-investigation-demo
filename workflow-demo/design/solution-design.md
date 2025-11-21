# AIOps Investigation Demo - System Design

## Overview

This project demonstrates an AI-powered Operations (AIOps) system that automatically investigates AWS infrastructure incidents using a multi-agent workflow. The system analyzes CloudWatch alarms, traces through AWS X-Ray, collects resource attributes, examines logs, and performs root cause analysis to provide actionable insights for incident resolution.

Full picture of the AIOps can check [design architecture](./design.excalidraw)

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CloudWatch    │    │   AWS X-Ray      │    │   CloudTrail    │
│     Alarms      │    │    Traces        │    │     Events      │
└─────────┬───────┘    └────────┬─────────┘    └─────────┬───────┘
          │                     │                        │
          └─────────────────────┼────────────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │   AIOps Investigation  │
                    │      Workflow          │
                    └───────────┬────────────┘
                                │
                    ┌───────────▼────────────┐
                    │   Multi-Agent System   │
                    │   (LangGraph-based)    │
                    └───────────┬────────────┘
                                │
                    ┌───────────▼────────────┐
                    │   Incident Analysis    │
                    │     & Resolution       │
                    └────────────────────────┘
```

### Workflow Architecture

The system uses a **LangGraph-based multi-agent workflow** with the following decision paths:

```
🔍 Alarm Analysis → 🤔 Decision Node → [Trace Path | Resource Path]
                                      ↓                    ↓
                            📊 Trace Graph Analysis    🤖 Domain Analysis
                                      ↓                    ↓
                            🔍 Trace Details Analysis  📊 Resource Collection
                                      ↓                    ↓
                            🔧 Trace Resource Collector    ↓
                                      ↓                    ↓
                                  📋 Logs Collection ←─────┘
                                      ↓
                              ☁️ CloudTrail Collection
                                      ↓
                              🔬 Root Cause Analysis
                                      ↓
                              📝 Incident Processing
```

## Core Components

### 1. Agent System

#### Base Agent (`src/agents/agent.py`)
- **Purpose**: Abstract base class for all AI agents
- **Features**: 
  - AWS Bedrock Claude integration
  - Standardized prompt templates
  - Error handling and logging
  - Tool integration support

#### Specialized Agents

##### Alarm Analyzer Agent (`src/agents/alarm_analyzer_agent.py`)
- **Purpose**: Analyzes CloudWatch alarms and extracts incident context
- **Inputs**: CloudWatch alarm data
- **Outputs**: Structured alarm analysis with affected resources
- **Key Features**:
  - Alarm severity assessment
  - Resource identification
  - Timeline extraction
  - Impact analysis

##### Decision Agent (`src/agents/decision_agent.py`)
- **Purpose**: Determines investigation path based on alarm analysis
- **Decision Logic**:
  - **Trace Path**: For distributed system issues with X-Ray traces
  - **Resource Path**: For infrastructure-specific issues
- **Outputs**: Recommended investigation strategy

##### Trace Graph Analyzer Agent (`src/agents/trace_graph_analyzer_agent.py`)
- **Purpose**: Analyzes AWS X-Ray service maps and trace graphs
- **Features**:
  - Service dependency mapping
  - Error rate analysis
  - Performance bottleneck identification
  - Service health assessment

##### Trace Details Analyzer Agent (`src/agents/trace_details_analyzer_agent.py`)
- **Purpose**: Deep-dive analysis of individual X-Ray traces
- **Features**:
  - Trace segment analysis
  - Error pattern identification
  - Performance anomaly detection
  - Resource correlation

##### Trace Resource Collector Agent (`src/agents/trace_resource_collector_agent.py`)
- **Purpose**: Collects detailed attributes for resources identified in traces
- **Features**:
  - Multi-resource attribute collection (EC2, Lambda, S3, RDS, DynamoDB, ELB)
  - Performance metrics gathering
  - Configuration analysis
  - Health status assessment

##### Logs Collector Agent (`src/agents/logs_collector_agent.py`)
- **Purpose**: Collects and analyzes CloudWatch logs for identified resources
- **Features**:
  - Time-based log filtering
  - Error pattern detection
  - Log correlation across services
  - Anomaly identification

##### CloudTrail Collector Agent (`src/agents/cloudtrail_collector_agent.py`)
- **Purpose**: Analyzes CloudTrail events for configuration changes
- **Features**:
  - LLM-powered event analysis
  - Configuration change detection
  - Policy modification tracking
  - Administrative action correlation

##### Root Cause Analysis Agent (`src/agents/root_cause_analysis_agent.py`)
- **Purpose**: Synthesizes all collected data to identify root causes
- **Features**:
  - Multi-source data correlation
  - Causal relationship analysis
  - Confidence scoring
  - Actionable recommendations

### 2. Node System

Each agent is wrapped in a corresponding node that handles:
- State management
- Context passing
- Error handling
- Logging and tracing
- Stream callback integration

**Node Structure**:
```
src/nodes/
├── alarm_analyzer_node.py
├── decision_node.py
├── trace_graph_analyzer_node.py
├── trace_details_analyzer_node.py
├── trace_resource_collector_node.py
├── logs_collector_node.py
├── cloudtrail_collector_node.py
├── root_cause_analysis_node.py
└── incident_processor_node.py
```

### 3. Tool System

#### AWS Integration Tools
- **X-Ray Tools** (`src/tools/xray_*`): Service map analysis, trace retrieval
- **CloudWatch Tools** (`src/tools/cloudwatch_*`): Metrics and logs collection
- **CloudTrail Tools** (`src/tools/cloudtrail_*`): Event analysis and filtering
- **Resource Tools** (`src/tools/resource_*`): Multi-service attribute collection

#### Utility Tools
- **JSON Utilities** (`utils/json_utils.py`): Safe JSON handling with control character cleaning
- **S3 Checksum Tools** (`demo/s3-checksum-demo.py`): Advanced S3 integrity validation

### 4. Context Management

#### Context Keys (`src/constants.py`)
```python
class ContextKeys:
    ALARM_ANALYSIS = "alarm_analysis"
    INITIAL_DECISION = "initial_decision"
    TRACE_GRAPH_ANALYSIS = "trace_graph_analysis"
    TRACE_ANALYSIS = "trace_analysis"
    TRACE_RESOURCES = "trace_resources"
    LOG_ANALYSIS = "log_analysis"
    CLOUDTRAIL_ANALYSIS = "cloudtrail_analysis"
    ROOT_CAUSE = "root_cause"
```

#### State Management
- **Persistent Context**: Maintains investigation state across nodes
- **Message Passing**: Structured JSON communication between agents
- **Stream Callbacks**: Real-time UI updates and progress tracking

## Key Features

### 1. Intelligent Path Selection
- **Trace Path**: For microservices and distributed system issues
- **Resource Path**: For infrastructure and configuration issues
- **Dynamic Routing**: Based on alarm characteristics and available data

### 2. Multi-Source Data Integration
- **CloudWatch**: Alarms, metrics, and logs
- **AWS X-Ray**: Distributed tracing and service maps
- **CloudTrail**: Configuration changes and administrative actions
- **Resource APIs**: EC2, Lambda, S3, RDS, DynamoDB, ELB attributes

### 3. Advanced Analysis Capabilities
- **Pattern Recognition**: Identifies common failure patterns
- **Correlation Analysis**: Links events across different data sources
- **Temporal Analysis**: Considers timing relationships
- **Impact Assessment**: Evaluates business and technical impact

### 4. Real-Time Streaming
- **Progress Tracking**: Live updates on investigation progress
- **Node Visibility**: Shows current processing stage
- **Error Handling**: Graceful degradation and error reporting

## Technical Implementation

### 1. LLM Integration
- **Model**: AWS Bedrock Claude (Anthropic)
- **Prompt Engineering**: Specialized prompts for each analysis type
- **Tool Integration**: Function calling for AWS API interactions
- **Context Management**: Maintains conversation context across agents

### 2. AWS SDK Integration
- **Boto3**: Primary AWS SDK for Python
- **Service Coverage**: CloudWatch, X-Ray, CloudTrail, EC2, Lambda, S3, RDS, DynamoDB, ELB
- **Error Handling**: Comprehensive AWS API error management
- **Retry Logic**: Exponential backoff for transient failures

### 3. Data Processing
- **JSON Handling**: Safe parsing with control character cleaning
- **Time Series Analysis**: CloudWatch metrics processing
- **Log Processing**: Pattern matching and anomaly detection
- **Checksum Validation**: Advanced S3 integrity checking (multipart support)

### 4. Workflow Engine
- **LangGraph**: State machine-based workflow orchestration
- **Conditional Routing**: Dynamic path selection based on analysis results
- **Parallel Processing**: Concurrent data collection where possible
- **Error Recovery**: Graceful handling of node failures

## Data Flow

### 1. Input Processing
```
CloudWatch Alarm → Alarm Analysis → Context Extraction → Path Decision
```

### 2. Trace Path Flow
```
X-Ray Service Map → Trace Details → Resource Collection → Log Analysis → CloudTrail → Root Cause
```

### 3. Resource Path Flow
```
Domain Analysis → Resource Collection → Log Analysis → CloudTrail → Root Cause
```

### 4. Output Generation
```
Root Cause Analysis → Incident Report → Actionable Recommendations
```

## Configuration

### 1. Environment Variables
- `AWS_REGION`: Default AWS region (ap-southeast-1)
- `AWS_PROFILE`: AWS credentials profile
- `LOG_LEVEL`: Logging verbosity
- `BEDROCK_MODEL`: Claude model configuration

### 2. Agent Configuration
- **Temperature**: LLM creativity setting (0 for deterministic)
- **Max Tokens**: Response length limits (200,000 for complex analysis)
- **Tool Selection**: Available tools per agent
- **Timeout Settings**: API call timeouts

### 3. Workflow Configuration
- **Path Selection Logic**: Decision criteria for trace vs resource paths
- **Relevance Thresholds**: Resource filtering criteria
- **Time Windows**: Log and event collection periods

## Monitoring and Observability

### 1. Logging
- **Structured Logging**: JSON-formatted logs with trace IDs
- **Node-Level Logging**: Detailed execution tracking
- **Error Logging**: Comprehensive error capture and context

### 2. Metrics
- **Execution Time**: Per-node and total workflow duration
- **Success Rates**: Node execution success tracking
- **Resource Usage**: Memory and CPU utilization

### 3. Tracing
- **Workflow Tracing**: End-to-end investigation tracking
- **Context Propagation**: Trace ID propagation across nodes
- **Debug Information**: Detailed execution context

## Security Considerations

### 1. AWS Permissions
- **Least Privilege**: Minimal required permissions per service
- **Role-Based Access**: IAM roles for different environments
- **Resource Scoping**: Limited access to investigation-relevant resources

### 2. Data Handling
- **Sensitive Data**: PII scrubbing and masking
- **Log Sanitization**: Control character cleaning
- **Secure Storage**: Temporary data encryption

### 3. API Security
- **Rate Limiting**: AWS API throttling compliance
- **Error Handling**: Secure error message handling
- **Credential Management**: Secure AWS credential handling

## Performance Optimization

### 1. Caching
- **Resource Attributes**: Cache frequently accessed resource data
- **API Responses**: Cache stable AWS API responses
- **Analysis Results**: Cache intermediate analysis results

### 2. Parallel Processing
- **Concurrent Collection**: Parallel resource attribute collection
- **Async Operations**: Non-blocking I/O operations
- **Batch Processing**: Efficient bulk data operations

### 3. Resource Management
- **Memory Optimization**: Efficient data structure usage
- **Connection Pooling**: Reuse AWS SDK connections
- **Cleanup**: Proper resource cleanup and garbage collection

## Testing Strategy

### 1. Unit Testing
- **Agent Testing**: Individual agent functionality
- **Tool Testing**: AWS integration tool validation
- **Utility Testing**: Helper function verification

### 2. Integration Testing
- **Workflow Testing**: End-to-end workflow validation
- **AWS Integration**: Real AWS service integration tests
- **Error Scenarios**: Failure mode testing

### 3. Demo Scenarios
- **S3 Checksum Demo**: Advanced S3 integrity validation
- **Multipart Analysis**: Large file checksum validation
- **JSON Processing**: Control character handling

## Deployment

### 1. Environment Setup
- **Python Dependencies**: Requirements management
- **AWS Configuration**: Credential and region setup
- **Environment Variables**: Configuration management

### 2. Scaling Considerations
- **Horizontal Scaling**: Multiple workflow instances
- **Resource Limits**: Memory and CPU constraints
- **API Quotas**: AWS service limit management

### 3. Monitoring
- **Health Checks**: System health monitoring
- **Performance Metrics**: Execution time tracking
- **Error Alerting**: Failure notification system

## Future Enhancements

### 1. Machine Learning Integration
- **Anomaly Detection**: ML-based pattern recognition
- **Predictive Analysis**: Proactive issue identification
- **Learning from History**: Pattern learning from past incidents

### 2. Extended AWS Service Support
- **Additional Services**: EKS, ECS, API Gateway, etc.
- **Cross-Service Correlation**: Enhanced service relationship mapping
- **Real-Time Streaming**: Live data processing

### 3. User Interface
- **Web Dashboard**: Real-time investigation visualization
- **Mobile Interface**: Mobile incident management
- **API Gateway**: RESTful API for external integration

### 4. Advanced Analytics
- **Business Impact Analysis**: Cost and revenue impact assessment
- **Compliance Reporting**: Regulatory compliance tracking
- **Trend Analysis**: Long-term pattern identification

## Conclusion

This AIOps Investigation Demo represents a comprehensive approach to automated incident investigation in AWS environments. By combining multiple AI agents with deep AWS integration, the system provides intelligent, context-aware analysis that significantly reduces mean time to resolution (MTTR) for infrastructure incidents.

The modular architecture allows for easy extension and customization, while the robust error handling and monitoring ensure reliable operation in production environments. The system demonstrates the power of combining large language models with domain-specific tools and knowledge to create truly intelligent operations automation.
