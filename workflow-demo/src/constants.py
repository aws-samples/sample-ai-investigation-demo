"""
Constants file for AIOps workflow
This file contains all shared attribute names and constants used across nodes and agents.
Centralizing these values allows for easy maintenance and consistency across the codebase.
"""

# =============================================================================
# CONTEXT ATTRIBUTE NAMES
# =============================================================================

class ContextKeys:
    """Context attribute names used across nodes and agents"""
    
    # Core workflow context keys
    INITIAL_DECISION = "initial_decision"
    ALARM_ANALYSIS = "alarm_analysis"
    TRACE_ANALYSIS = "trace_analysis"
    DOMAIN_ANALYSIS = "domain_analysis"
    RESOURCE_INFO = "resource_info"
    ROOT_CAUSE = "root_cause"
    TRACE_ID = "trace_id"
    
    # AWS context keys
    REGION = "region"
    ACCOUNT_ID = "account_id"
    
    # Split collector context keys
    LOGS_ANALYSIS = "logs_analysis"
    CLOUDTRAIL_ANALYSIS = "cloudtrail_analysis"
    
    # Trace-specific context keys
    TRACE_RESOURCES = "resource_collection"
    TRACE_GRAPH_ANALYSIS = "trace_graph_analysis"


class AgentTypes:
    XML_AGENT = "xml"
    FUNCTION_CALL_AGENT = "calling"
    STRUCTURED_CHAT_AGENT = "structured_chat"

# =============================================================================
# MESSAGE ATTRIBUTE NAMES
# =============================================================================

class MessageKeys:
    """Message attribute names used in workflow communication"""
    
    # Standard message structure
    CONTENT = "content"
    MESSAGES = "messages"
    
    # Decision node output keys
    DECISION = "decision"
    ALARM_SUMMARY = "alarm_summary"
    
    # Analysis output keys
    RAW_ANALYSIS = "raw_analysis"
    RELEVANT_RESOURCES = "relevant_resources"
    RECOMMENDED_ACTIONS = "recommended_actions"


# =============================================================================
# ANALYSIS RESULT ATTRIBUTE NAMES
# =============================================================================

class AnalysisKeys:
    """Attribute names used in analysis results"""
    
    # Common analysis attributes
    ALERT_TYPE = "alert_type"
    RESOURCE_TYPE = "resource_type"
    SEVERITY = "severity"
    CONFIDENCE_SCORE = "confidence_score"
    IDENTIFIED_CAUSE = "identified_cause"
    
    # Decision analysis attributes
    RECOMMENDED_PATH = "recommended_path"
    REASONING = "reasoning"
    
    # Alarm analysis attributes
    IDENTIFIED_ALARM_TYPES = "identified_alarm_types"
    EXTRACTED_INFO = "extracted_info"
    POSSIBLE_CAUSES = "possible_causes"
    ADDITIONAL_INFO = "additional_info"
    
    # Resource analysis attributes
    RESOURCE_ID = "resource_id"
    RESOURCE_NAME = "resource_name"
    IDENTIFIED_RESOURCES = "identified_resources"
    POTENTIAL_ISSUES = "potential_issues"
    
    # Trace analysis attributes
    TRACE = "trace"
    METRICS = "metrics"
    ERROR_TRACES = "error_traces"
    SERVICE_MAP = "service_map"
    TRACE_SUMMARIES = "trace_summaries"
    
    # Root cause analysis attributes
    CONTRIBUTING_FACTORS = "contributing_factors"
    EVIDENCE_ANALYSIS = "evidence_analysis"
    PREVENTION_MEASURES = "prevention_measures"
    RELATED_FACTORS = "related_factors"
    EVIDENCE = "evidence"


# =============================================================================
# DATA STRUCTURE ATTRIBUTE NAMES
# =============================================================================

class DataKeys:
    """Attribute names used in data structures"""
    
    # Log data structure
    LOGS = "logs"
    SUMMARY = "summary"
    
    # CloudTrail data structure
    EVENTS = "events"
    CONFIG = "config"
    
    # Trace data structure
    FINDINGS = "findings"
    START_TIME = "start_time"
    DURATION = "duration"
    ERROR = "error"
    PATH = "path"
    
    # Resource data structure
    API_DETAILS = "api_details"
    STAGE_DETAILS = "stage_details"
    DB_DETAILS = "db_details"
    
    # Common data attributes
    TIMESTAMP = "timestamp"
    MESSAGE = "message"
    VALUE = "value"
    NAME = "name"
    TYPE = "type"
    STATUS = "status"


# =============================================================================
# WORKFLOW PATH CONSTANTS
# =============================================================================

class WorkflowPaths:
    """Workflow path constants"""
    
    TRACE = "trace"
    RESOURCE = "resource"
    CRITICAL = "critical"


# =============================================================================
# SEVERITY LEVELS
# =============================================================================

class SeverityLevels:
    """Severity level constants"""
    
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


# =============================================================================
# ALERT TYPES
# =============================================================================

class AlertTypes:
    """Alert type constants"""
    
    PERFORMANCE = "performance"
    AVAILABILITY = "availability"
    ERROR = "error"
    SECURITY = "security"
    RESOURCE = "resource"
    NETWORK = "network"


# =============================================================================
# RESOURCE TYPES
# =============================================================================

class ResourceTypes:
    """AWS resource type constants"""
    
    API_GATEWAY = "AWS::ApiGateway::RestApi"
    LAMBDA = "AWS::Lambda::Function"
    RDS = "AWS::RDS::DBInstance"
    EC2 = "AWS::EC2::Instance"
    ELB = "AWS::ElasticLoadBalancing::LoadBalancer"
    CLOUDFRONT = "AWS::CloudFront::Distribution"
    S3 = "AWS::S3::Bucket"
    DYNAMODB = "AWS::DynamoDB::Table"
    SNS = "AWS::SNS::Topic"
    SQS = "AWS::SQS::Queue"


# =============================================================================
# NODE NAMES
# =============================================================================

class NodeNames:
    """Node name constants for the workflow graph"""
    
    ALARM_ANALYZER = "alarm_analyzer"
    DECISION = "decision"
    TRACE_GRAPH_ANALYZER = "trace_graph_analyzer"
    TRACE_DETAILS_ANALYZER = "trace_details_analyzer"
    TRACE_RESOURCE_COLLECTOR = "trace_resource_collector"
    DOMAIN_BOT = "domain_bot"
    RESOURCE_COLLECTOR = "resource_collector"
    LOGS_COLLECTOR = "logs_collector"
    CLOUDTRAIL_COLLECTOR = "cloudtrail_collector"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    INCIDENT_PROCESSOR = "incident_processor"


# =============================================================================
# AGENT NAMES
# =============================================================================

class AgentNames:
    """Agent name constants"""
    
    ALARM_ANALYZER_AGENT = "Alarm Analyzer Agent"
    DECISION_AGENT = "Decision Agent"
    TRACE_GRAPH_ANALYZER_AGENT = "Trace Graph Analyzer Agent"
    TRACE_DETAILS_ANALYZER_AGENT = "Trace Details Analyzer Agent"
    TRACE_RESOURCE_COLLECTOR_AGENT = "Trace Resource Collector Agent"
    DOMAIN_BOT_AGENT = "Domain Bot Agent"
    RESOURCE_COLLECTOR_AGENT = "Resource Collector Agent"
    LOGS_COLLECTOR_AGENT = "Logs Collector Agent"
    CLOUDTRAIL_COLLECTOR_AGENT = "CloudTrail Collector Agent"
    ROOT_CAUSE_ANALYSIS_AGENT = "Root Cause Analysis Agent"
    INCIDENT_PROCESSOR_AGENT = "Incident Processor Agent"


# =============================================================================
# LOGGING CONSTANTS
# =============================================================================

class LoggerNames:
    """Logger name constants"""
    
    ALARM_ANALYZER = "aiops_node_alarm_analyzer"
    DECISION = "aiops_node_decision"
    TRACE_GRAPH_ANALYZER = "aiops_node_trace_graph_analyzer"
    TRACE_DETAILS_ANALYZER = "aiops_node_trace_details_analyzer"
    TRACE_RESOURCE_COLLECTOR = "aiops_node_trace_resource_collector"
    DOMAIN_BOT = "aiops_node_domain_bot"
    RESOURCE_COLLECTOR = "aiops_node_resource_collector"
    LOGS_COLLECTOR = "aiops_node_logs_collector"
    CLOUDTRAIL_COLLECTOR = "aiops_node_cloudtrail_collector"
    ROOT_CAUSE_ANALYSIS = "aiops_node_root_cause_analysis"
    INCIDENT_PROCESSOR = "aiops_node_incident_processor"
    WORKFLOW = "aiops_workflow"
    STREAMLIT = "aiops_streamlit"


# =============================================================================
# ERROR MESSAGES
# =============================================================================

class ErrorMessages:
    """Common error message constants"""
    
    MISSING_CONTEXT = "Missing required context data"
    INVALID_INPUT = "Invalid input format"
    AGENT_EXECUTION_ERROR = "Error in agent execution"
    JSON_PARSE_ERROR = "Error parsing JSON response"
    INSUFFICIENT_DATA = "Insufficient data for analysis"
    TIMEOUT_ERROR = "Operation timed out"
    AUTHENTICATION_ERROR = "Authentication failed"
    RESOURCE_NOT_FOUND = "Resource not found"


# =============================================================================
# SUCCESS MESSAGES
# =============================================================================

class SuccessMessages:
    """Common success message constants"""
    
    ANALYSIS_COMPLETED = "Analysis completed successfully"
    DATA_COLLECTED = "Data collection completed"
    CONTEXT_UPDATED = "Context updated successfully"
    AGENT_EXECUTED = "Agent executed successfully"
    WORKFLOW_COMPLETED = "Workflow completed successfully"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_all_context_keys():
    """Get all context keys as a list"""
    return [getattr(ContextKeys, attr) for attr in dir(ContextKeys) if not attr.startswith('_')]

def get_all_message_keys():
    """Get all message keys as a list"""
    return [getattr(MessageKeys, attr) for attr in dir(MessageKeys) if not attr.startswith('_')]

def get_all_analysis_keys():
    """Get all analysis keys as a list"""
    return [getattr(AnalysisKeys, attr) for attr in dir(AnalysisKeys) if not attr.startswith('_')]

def validate_context_keys(context_dict):
    """Validate that context dictionary uses standard keys"""
    valid_keys = get_all_context_keys()
    invalid_keys = [key for key in context_dict.keys() if key not in valid_keys]
    return len(invalid_keys) == 0, invalid_keys

def validate_required_context_keys(context_dict, required_keys):
    """Validate that required context keys are present"""
    missing_keys = [key for key in required_keys if key not in context_dict]
    return len(missing_keys) == 0, missing_keys
