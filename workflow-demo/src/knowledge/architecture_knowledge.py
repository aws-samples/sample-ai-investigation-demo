"""
Architecture Knowledge Base for AIOps workflow
This module provides RAG-style access to information about application architecture,
component relationships, and troubleshooting guidance.
"""

import json
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool

# Application architecture knowledge base
ARCHITECTURE_KNOWLEDGE = {
    "e-commerce-platform": {
        "description": "Microservices-based e-commerce platform",
        "components": {
            "frontend-service": {
                "type": "React SPA",
                "hosting": "S3 + CloudFront",
                "dependencies": ["api-gateway", "auth-service"],
                "monitoring": ["CloudWatch", "X-Ray"],
                "common_issues": [
                    "Slow page loads due to large asset sizes",
                    "CORS configuration errors with API Gateway",
                    "CloudFront cache invalidation delays"
                ]
            },
            "api-gateway": {
                "type": "AWS API Gateway",
                "dependencies": ["product-service", "cart-service", "order-service", "auth-service"],
                "monitoring": ["CloudWatch", "X-Ray"],
                "common_issues": [
                    "Rate limiting during high traffic",
                    "Integration timeout with backend services",
                    "Authorization failures with custom authorizers"
                ]
            },
            "product-service": {
                "type": "Lambda + DynamoDB",
                "dependencies": ["inventory-service", "pricing-service", "product-db"],
                "monitoring": ["CloudWatch", "X-Ray", "Custom metrics"],
                "common_issues": [
                    "DynamoDB throttling during high traffic",
                    "Lambda cold starts affecting response time",
                    "Inventory synchronization delays"
                ]
            },
            "cart-service": {
                "type": "Lambda + DynamoDB",
                "dependencies": ["product-service", "cart-db"],
                "monitoring": ["CloudWatch", "X-Ray"],
                "common_issues": [
                    "Session expiration issues",
                    "Race conditions during concurrent updates",
                    "Inconsistent cart state after service failures"
                ]
            },
            "order-service": {
                "type": "ECS Fargate + Aurora",
                "dependencies": ["payment-service", "inventory-service", "notification-service", "order-db"],
                "monitoring": ["CloudWatch", "X-Ray", "Custom metrics"],
                "common_issues": [
                    "Database connection pool exhaustion",
                    "Transaction timeouts during peak loads",
                    "Payment processing delays"
                ]
            },
            "payment-service": {
                "type": "Lambda + Step Functions",
                "dependencies": ["payment-gateway", "fraud-detection-service"],
                "monitoring": ["CloudWatch", "X-Ray", "Custom metrics"],
                "common_issues": [
                    "Payment gateway timeouts",
                    "Step Function execution failures",
                    "Idempotency issues with retries"
                ]
            },
            "inventory-service": {
                "type": "ECS Fargate + Aurora",
                "dependencies": ["warehouse-system", "inventory-db"],
                "monitoring": ["CloudWatch", "X-Ray"],
                "common_issues": [
                    "Inventory inconsistencies during high concurrency",
                    "Slow synchronization with warehouse systems",
                    "Lock contention in database"
                ]
            },
            "auth-service": {
                "type": "Cognito + Lambda",
                "dependencies": ["user-db"],
                "monitoring": ["CloudWatch", "X-Ray"],
                "common_issues": [
                    "Token validation failures",
                    "Rate limiting during login spikes",
                    "Custom authentication workflow failures"
                ]
            },
            "notification-service": {
                "type": "Lambda + SNS + SQS",
                "dependencies": ["email-service", "sms-service"],
                "monitoring": ["CloudWatch", "X-Ray"],
                "common_issues": [
                    "Message delivery delays",
                    "SQS DLQ accumulation",
                    "Email deliverability issues"
                ]
            }
        },
        "data_flows": [
            {
                "name": "Product Browse Flow",
                "path": ["frontend-service", "api-gateway", "product-service"],
                "expected_latency": "< 200ms"
            },
            {
                "name": "Add to Cart Flow",
                "path": ["frontend-service", "api-gateway", "cart-service", "product-service"],
                "expected_latency": "< 300ms"
            },
            {
                "name": "Checkout Flow",
                "path": ["frontend-service", "api-gateway", "order-service", "payment-service", "inventory-service", "notification-service"],
                "expected_latency": "< 2s"
            },
            {
                "name": "Authentication Flow",
                "path": ["frontend-service", "api-gateway", "auth-service"],
                "expected_latency": "< 500ms"
            }
        ]
    },
    "analytics-platform": {
        "description": "Data analytics platform for business intelligence",
        "components": {
            "data-ingestion": {
                "type": "Kinesis Firehose",
                "dependencies": ["s3-raw-bucket", "lambda-transformers"],
                "monitoring": ["CloudWatch", "X-Ray", "Custom metrics"],
                "common_issues": [
                    "Data delivery delays during high volume",
                    "Lambda transformation timeouts",
                    "Schema validation failures"
                ]
            },
            "data-processing": {
                "type": "EMR + Spark",
                "dependencies": ["s3-raw-bucket", "s3-processed-bucket", "glue-catalog"],
                "monitoring": ["CloudWatch", "Ganglia", "Custom metrics"],
                "common_issues": [
                    "Cluster scaling delays",
                    "Job failures due to data skew",
                    "Memory pressure on executors"
                ]
            },
            "data-warehouse": {
                "type": "Redshift",
                "dependencies": ["s3-processed-bucket"],
                "monitoring": ["CloudWatch", "Performance Insights"],
                "common_issues": [
                    "Long-running queries blocking resources",
                    "WLM queue waits during peak times",
                    "Vacuum operations affecting performance"
                ]
            },
            "query-service": {
                "type": "Lambda + API Gateway",
                "dependencies": ["data-warehouse", "athena-service"],
                "monitoring": ["CloudWatch", "X-Ray"],
                "common_issues": [
                    "Query timeouts for complex analytics",
                    "Result set size limitations",
                    "Concurrent query limits"
                ]
            },
            "visualization": {
                "type": "QuickSight",
                "dependencies": ["data-warehouse", "query-service"],
                "monitoring": ["CloudWatch"],
                "common_issues": [
                    "Dashboard loading delays",
                    "SPICE refresh failures",
                    "Data permission issues"
                ]
            }
        },
        "data_flows": [
            {
                "name": "Data Ingestion Flow",
                "path": ["data-ingestion", "s3-raw-bucket", "lambda-transformers"],
                "expected_latency": "< 1 minute"
            },
            {
                "name": "Batch Processing Flow",
                "path": ["data-processing", "s3-processed-bucket", "data-warehouse"],
                "expected_latency": "< 1 hour"
            },
            {
                "name": "Query Flow",
                "path": ["visualization", "query-service", "data-warehouse"],
                "expected_latency": "< 5s"
            }
        ]
    }
}

@tool("get_architecture_info")
def get_architecture_info(application_name: str) -> str:
    """
    Get detailed information about a specific application architecture.
    
    Args:
        application_name: The name of the application architecture to look up
        
    Returns:
        String containing detailed information about the application architecture
    """
    application_name = application_name.strip().lower()
    
    # Check if the application exists in our knowledge base
    if application_name in ARCHITECTURE_KNOWLEDGE:
        app_data = ARCHITECTURE_KNOWLEDGE[application_name]
        return json.dumps(app_data, indent=2)
    else:
        # Check for partial matches
        possible_matches = [name for name in ARCHITECTURE_KNOWLEDGE.keys() 
                           if application_name in name.lower()]
        
        if possible_matches:
            return f"Exact application '{application_name}' not found. Did you mean one of these? {', '.join(possible_matches)}"
        else:
            return f"No information found for application '{application_name}'. Available applications: {', '.join(ARCHITECTURE_KNOWLEDGE.keys())}"

@tool("list_applications")
def list_applications() -> str:
    """
    List all available application architectures in the knowledge base.
    
    Returns:
        String containing a list of all available application architectures
    """
    app_list = []
    for app_name, data in ARCHITECTURE_KNOWLEDGE.items():
        app_list.append(f"{app_name}: {data['description']}")
    
    return "\n".join(app_list)

@tool("get_component_info")
def get_component_info(application_name: str, component_name: str) -> str:
    """
    Get detailed information about a specific component within an application architecture.
    
    Args:
        application_name: The name of the application architecture
        component_name: The name of the component to look up
        
    Returns:
        String containing detailed information about the component
    """
    application_name = application_name.strip().lower()
    component_name = component_name.strip().lower()
    
    # Check if the application exists in our knowledge base
    if application_name in ARCHITECTURE_KNOWLEDGE:
        app_data = ARCHITECTURE_KNOWLEDGE[application_name]
        
        # Check if the component exists in the application
        components = {k.lower(): v for k, v in app_data["components"].items()}
        if component_name in components:
            component_data = components[component_name]
            return json.dumps(component_data, indent=2)
        else:
            # Check for partial matches
            possible_matches = [name for name in app_data["components"].keys() 
                               if component_name in name.lower()]
            
            if possible_matches:
                return f"Exact component '{component_name}' not found. Did you mean one of these? {', '.join(possible_matches)}"
            else:
                return f"No information found for component '{component_name}'. Available components: {', '.join(app_data['components'].keys())}"
    else:
        return f"No information found for application '{application_name}'. Available applications: {', '.join(ARCHITECTURE_KNOWLEDGE.keys())}"

@tool("get_data_flow")
def get_data_flow(application_name: str, flow_name: str = None) -> str:
    """
    Get information about data flows within an application architecture.
    
    Args:
        application_name: The name of the application architecture
        flow_name: Optional name of a specific data flow to look up
        
    Returns:
        String containing information about data flows
    """
    application_name = application_name.strip().lower()
    
    # Check if the application exists in our knowledge base
    if application_name in ARCHITECTURE_KNOWLEDGE:
        app_data = ARCHITECTURE_KNOWLEDGE[application_name]
        
        if flow_name:
            flow_name = flow_name.strip().lower()
            # Look for a specific flow
            for flow in app_data["data_flows"]:
                if flow_name.lower() in flow["name"].lower():
                    return json.dumps(flow, indent=2)
            
            return f"No data flow found with name '{flow_name}'. Available flows: {', '.join([flow['name'] for flow in app_data['data_flows']])}"
        else:
            # Return all flows
            return json.dumps(app_data["data_flows"], indent=2)
    else:
        return f"No information found for application '{application_name}'. Available applications: {', '.join(ARCHITECTURE_KNOWLEDGE.keys())}"
