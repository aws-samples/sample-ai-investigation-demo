"""
Trace Resource Collector Agent in the AIOps workflow

Your role is to collect detailed resource attributes and metrics information about the resources either affected by the CloudWatch alert or relevant. You shall be provided with a json formatted input with 'affected_resources' and 'relevant_resources'. However, the tool only supports collecting attributes for the following AWS resources:
EC2/S3/RDS/DynamoDB/Lambda/ELB/ALB.

You should follow these steps:
1. get all relevant resource from the input data and form a list of resource ARNs.
2. confirm the resources are in the supported list
3. remove the unsupported resources from the list
4. use the collect_aws_resource_attributes tool to collect detailed attributes and metrics for the supported resources


EC2: Collecting detailed attributes for EC2 instances (metrics, status, configuration)
Lambda Functions: Gathering Lambda function metrics (invocations, errors, duration, memory usage)
S3: Retrieving S3 bucket information (bucket policy, access logs, metrics)
RDS: Collecting RDS database metrics and configuration
DynamoDB: Collecting DynamoDB table metrics and configuration
ELB/ALB: Gathering ELB/ALB metrics and health check information

Your analysis should focus on:
- Performance metrics and resource utilization
- Configuration issues and misconfigurations
- Security-related findings
- Resource dependencies and relationships

Output MUST be strictly in JSON format with the following structure:
- resource_collection: json object with the following attributes:
    - ec2_resources: List of EC2 instances with metrics and status
    - lambda_resources: List of Lambda functions with key metrics
    - s3_resources: List of S3 buckets with policies and metrics
    - rds_resources: List of RDS instances with performance metrics
    - dynamodb_resources: List of DynamoDB tables with metrics
    - elb_resources: List of ELB/ALB resources with health metrics
- raw_analysis: "Detailed analysis of the resource collection findings"
- recommendations: List of actionable recommendations based on the findings
"""

import sys
import os
import json
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import get_bedrock_model, create_prompt_template, create_agent_executor, COMMON_TOOLS
from agents.agent import Agent

# Import the existing tools
from tools.resource_attributes_collector import ResourceAttributesCollector
from tools.resource_utils import (
    collect_multiple_resource_attributes,
    extract_resource_arns_from_text,
    format_resource_collection_for_display
)

# Import constants
from constants import ContextKeys, AnalysisKeys

# Create a simple tool that uses our existing resource collector
from typing import Union, List

@tool
def collect_aws_resource_attributes(resource_arns_text: Union[str, List[str]], region: str = "ap-southeast-1") -> str:
    """
    Collect detailed attributes and metrics for AWS resources using the existing resource collector tool.
    
    Args:
        resource_arns_text: AWS resource ARNs (can be a string with comma-separated ARNs, JSON array string, or list of ARNs)
        region: AWS region for resources (default: ap-southeast-1). If not provided, will try to extract from ARNs.
    
    Returns:
        JSON string containing comprehensive resource attributes and metrics
    """
    try:
        # Handle different input formats
        resource_arns = []
        
        # If input is already a list, use it directly
        if isinstance(resource_arns_text, list):
            resource_arns = resource_arns_text
        elif isinstance(resource_arns_text, str):
            # Extract ARNs from the input text
            resource_arns = extract_resource_arns_from_text(resource_arns_text)
            
            if not resource_arns:
                # Try parsing as JSON array
                if resource_arns_text.strip().startswith('['):
                    try:
                        resource_arns = json.loads(resource_arns_text)
                    except json.JSONDecodeError:
                        pass
                else:
                    # Try comma-separated
                    resource_arns = [arn.strip() for arn in resource_arns_text.split(',') if arn.strip()]
        
        # If still no ARNs found, try to parse the input as a single ARN
        if not resource_arns and isinstance(resource_arns_text, str) and resource_arns_text.strip():
            resource_arns = [resource_arns_text.strip()]
        
        # If region not provided or is default, try to extract from ARNs
        aws_region = region
        if not resource_arns:
            return json.dumps({
                "error": "No valid resource ARNs found in input",
                "input_received": str(resource_arns_text),
                "input_type": str(type(resource_arns_text)),
                "resource_collection": {
                    "ec2_resources": [],
                    "lambda_resources": [],
                    "s3_resources": [],
                    "rds_resources": [],
                    "apigateway_resources": [],
                    "dynamodb_resources": [],
                    "elb_resources": []
                }
            })
        
        # Try to extract region from the first ARN if region is default
        if aws_region == "ap-southeast-1" and resource_arns:
            try:
                first_arn = resource_arns[0]
                arn_parts = first_arn.split(':')
                if len(arn_parts) >= 4 and arn_parts[3]:
                    aws_region = arn_parts[3]
            except:
                pass  # Use default region
        
        print(f"Collecting attributes for {len(resource_arns)} resources in region {aws_region}")
        print(f"Resource ARNs: {resource_arns}")
        
        # Use the existing resource collector
        result = collect_multiple_resource_attributes(resource_arns, aws_region)
        
        # Format the result for display
        formatted_result = format_resource_collection_for_display(result)
        
        return json.dumps({
            "resource_collection": result,
            "formatted_analysis": formatted_result,
            "region_used": aws_region,
            "total_resources": len(resource_arns),
            "resource_arns": resource_arns
        }, indent=2, default=str)
        
    except Exception as e:
        return json.dumps({
            "error": f"Failed to collect resource attributes: {str(e)}",
            "input_received": str(resource_arns_text),
            "input_type": str(type(resource_arns_text)),
            "region_attempted": region,
            "error_type": type(e).__name__,
            "resource_collection": {
                "ec2_resources": [],
                "lambda_resources": [],
                "s3_resources": [],
                "rds_resources": [],
                "apigateway_resources": [],
                "dynamodb_resources": [],
                "elb_resources": []
            }
        })
        
        if not resource_arns:
            return json.dumps({
                "error": "No valid resource ARNs found in input",
                "resource_collection": {
                    "ec2_resources": [],
                    "lambda_resources": [],
                    "s3_resources": [],
                    "rds_resources": [],
                    "apigateway_resources": [],
                    "dynamodb_resources": [],
                    "elb_resources": []
                }
            })
        
        # Log the ARNs and region being used
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Collecting attributes for {len(resource_arns)} resources in region {aws_region}")
        for arn in resource_arns:
            logger.info(f"  - {arn}")
        
        # Use the existing resource collection tool with AWS region
        results = collect_multiple_resource_attributes(
            resource_arns=resource_arns,
            region_name=aws_region
        )
        
        # Format for display
        formatted_display = format_resource_collection_for_display(results)
        
        return json.dumps({
            "resource_collection": results,
            "formatted_display": formatted_display
        }, default=str)
        
    except Exception as e:
        return json.dumps({
            "error": f"Error collecting resource attributes: {str(e)}",
            "resource_collection": {
                "ec2_resources": [],
                "lambda_resources": [],
                "s3_resources": [],
                "rds_resources": [],
                "apigateway_resources": [],
                "dynamodb_resources": [],
                "elb_resources": []
            }
        })

# Enhanced tool list with our resource collector
TRACE_RESOURCE_COLLECTOR_TOOLS = COMMON_TOOLS + [collect_aws_resource_attributes]

class TraceResourceCollectorAgent(Agent):
    """Trace Resource Collector Agent for detailed resource attribute collection"""
    
    def __init__(self):
        """Initialize the Trace Resource Collector Agent"""
        super().__init__("Trace Resource Collector Agent")
        self.prompt = create_prompt_template("Trace Resource Collector Agent", __doc__)
        
        # Add the resource collector tool to the common tools
        self.agent_executor = create_agent_executor(self.model, TRACE_RESOURCE_COLLECTOR_TOOLS, self.prompt)
    
    def process(self, input_data):
        """
        Process the input data and return resource collection results
        
        Args:
            input_data: Input data containing resource information
            
        Returns:
            JSON string containing resource collection results with TRACE_RESOURCES key
        """
        try:
            # Let the agent handle the resource collection
            result = self.agent_executor.invoke({
                "input": f"Collect detailed resource attributes and metrics for these resources:\n\n{input_data}"
            })
            
            agent_output = result["output"]
            
            # Try to parse the agent output as JSON
            try:
                parsed_output = json.loads(agent_output)
                
                # Wrap the output with the TRACE_RESOURCES key for stream callback detection
                wrapped_output = {
                    ContextKeys.TRACE_RESOURCES: parsed_output,
                    "resource_collection": parsed_output.get("resource_collection", {}),
                    "raw_analysis": parsed_output.get("raw_analysis", ""),
                    "recommendations": parsed_output.get("recommendations", [])
                }
                
                return json.dumps(wrapped_output, indent=2, default=str)
                
            except json.JSONDecodeError:
                # If agent output is not JSON, wrap it anyway
                wrapped_output = {
                    ContextKeys.TRACE_RESOURCES: {
                        "raw_analysis": agent_output,
                        "resource_collection": {
                            "ec2_resources": [],
                            "lambda_resources": [],
                            "s3_resources": [],
                            "rds_resources": [],
                            "apigateway_resources": [],
                            "dynamodb_resources": [],
                            "elb_resources": []
                        }
                    },
                    "resource_collection": {},
                    "raw_analysis": agent_output,
                    "recommendations": []
                }
                
                return json.dumps(wrapped_output, indent=2)
            
        except Exception as e:
            # Handle errors gracefully
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error invoking trace resource collector agent: {e}", exc_info=True)
            
            # Create a proper JSON error response with TRACE_RESOURCES key
            error_response = {
                ContextKeys.TRACE_RESOURCES: {
                    "resource_collection": {
                        "ec2_resources": [],
                        "lambda_resources": [],
                        "s3_resources": [],
                        "rds_resources": [],
                        "apigateway_resources": [],
                        "dynamodb_resources": [],
                        "elb_resources": [],
                        "error": f"Error in trace resource collection: {str(e)}"
                    },
                    "raw_analysis": f"Trace resource collection failed: {str(e)}",
                    "recommendations": []
                },
                "resource_collection": {},
                "raw_analysis": f"Trace resource collection failed: {str(e)}",
                "recommendations": []
            }
            
            return json.dumps(error_response, indent=2)
