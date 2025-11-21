"""
X-Ray Service Graph Tool

This tool provides functionality to retrieve and analyze AWS X-Ray service graphs
for a specified time range and region. It's designed to be used by agents to get service topology
information without having to use the AWS CLI directly.

Usage:
- get_xray_service_graph("360,ap-southeast-1") - Get service graph for the last 360 minutes in ap-southeast-1 region
- analyze_xray_service_graph("360,us-west-2") - Analyze service graph for the last 360 minutes in us-west-2 region

The region parameter is optional and defaults to ap-southeast-1.
"""

import boto3
import json
import time
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool

# Set up logging
logger = logging.getLogger(__name__)

class XRayServiceGraphTool:
    """Tool for retrieving and analyzing AWS X-Ray service graphs"""
    
    def __init__(self, region_name: Optional[str] = None):
        """
        Initialize the X-Ray service graph tool
        
        Args:
            region_name: AWS region name (optional, defaults to session default)
        """
        self.region_name = region_name
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the X-Ray client"""
        try:
            if self.region_name:
                self.xray_client = boto3.client('xray', region_name=self.region_name)
            else:
                self.xray_client = boto3.client('xray')
            
            # Get the actual region being used
            self.region_name = self.xray_client.meta.region_name
            logger.info(f"Initialized X-Ray client in region: {self.region_name}")
            
        except Exception as e:
            logger.error(f"Error initializing X-Ray client: {e}")
            raise
    
    def get_service_graph(self, minutes: int = 15, start_time: Optional[datetime] = None, 
                         end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get the X-Ray service graph for a specified time range
        
        Args:
            minutes: Number of minutes to look back from now (default: 15)
            start_time: Explicit start time (optional, overrides minutes)
            end_time: Explicit end time (optional, defaults to now)
            
        Returns:
            Dict containing the service graph data
        """
        try:
            # Set up time range
            if end_time is None:
                end_time = datetime.now()  # Use local time instead of UTC
            
            if start_time is None:
                start_time = end_time - timedelta(minutes=minutes)
            
            # Convert to Unix timestamps
            start_timestamp = int(start_time.timestamp())
            end_timestamp = int(end_time.timestamp())
            
            logger.info(f"Getting service graph from {start_time} to {end_time}")
            
            # Call X-Ray API
            response = self.xray_client.get_service_graph(
                StartTime=start_timestamp,
                EndTime=end_timestamp
            )
            
            # Process the response
            service_graph = self._process_service_graph(response)
            
            return service_graph
            
        except Exception as e:
            logger.error(f"Error getting service graph: {e}")
            return {
                "error": str(e),
                "service_graph": {},
                "services": [],
                "edges": []
            }
    
    def _process_service_graph(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the raw X-Ray service graph response
        
        Args:
            response: Raw X-Ray API response
            
        Returns:
            Dict containing processed service graph data
        """
        services = []
        edges = []
        
        # Process services
        for service in response.get('Services', []):
            service_data = {
                'name': service.get('Name', 'unknown'),
                'type': service.get('Type', 'unknown'),
                'account_id': service.get('AccountId', 'unknown'),
                'request_count': service.get('SummaryStatistics', {}).get('TotalCount', 0),
                'error_count': service.get('SummaryStatistics', {}).get('ErrorStatistics', {}).get('TotalCount', 0),
                'fault_count': service.get('SummaryStatistics', {}).get('FaultStatistics', {}).get('TotalCount', 0),
                'total_response_time': service.get('SummaryStatistics', {}).get('TotalResponseTime', 0),
                'avg_response_time': 0
            }
            
            # Calculate average response time
            if service_data['request_count'] > 0:
                service_data['avg_response_time'] = service_data['total_response_time'] / service_data['request_count']
            
            # Calculate error rate
            if service_data['request_count'] > 0:
                service_data['error_rate'] = (service_data['error_count'] + service_data['fault_count']) / service_data['request_count'] * 100
            else:
                service_data['error_rate'] = 0
            
            services.append(service_data)
        
        # Process edges
        for service in response.get('Services', []):
            for edge in service.get('Edges', []):
                edge_data = {
                    'from': service.get('ReferenceId', 0),
                    'to': edge.get('ReferenceId', 0),
                    'request_count': edge.get('SummaryStatistics', {}).get('TotalCount', 0),
                    'error_count': edge.get('SummaryStatistics', {}).get('ErrorStatistics', {}).get('TotalCount', 0),
                    'fault_count': edge.get('SummaryStatistics', {}).get('FaultStatistics', {}).get('TotalCount', 0)
                }
                edges.append(edge_data)
        
        # Find root service
        root_service = None
        for service in response.get('Services', []):
            if service.get('Root', False):
                root_service_data = next((s for s in services if s['name'] == service.get('Name', 'unknown')), None)
                if root_service_data:
                    root_service = root_service_data
                    break
        
        # Calculate overall statistics
        total_requests = sum(service['request_count'] for service in services)
        total_errors = sum(service['error_count'] + service['fault_count'] for service in services)
        overall_error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'services': services,
            'edges': edges,
            'root_service': root_service,
            'total_services': len(services),
            'total_requests': total_requests,
            'total_errors': total_errors,
            'overall_error_rate': overall_error_rate,
            'start_time': response.get('StartTime'),
            'end_time': response.get('EndTime'),
            'region': self.region_name
        }
    
    def analyze_service_graph(self, service_graph: Dict[str, Any], 
                             max_relevant_nodes: int = 3) -> Dict[str, Any]:
        """
        Analyze the service graph to identify problematic nodes
        
        Args:
            service_graph: Service graph data from get_service_graph
            max_relevant_nodes: Maximum number of relevant nodes to return
            
        Returns:
            Dict containing analysis results
        """
        try:
            services = service_graph.get('services', [])
            if not services:
                return {
                    "error": "No services found in service graph",
                    "relevant_nodes": []
                }
            
            # Sort services by error rate (descending)
            services_by_error = sorted(
                services, 
                key=lambda x: x.get('error_rate', 0), 
                reverse=True
            )
            
            # Sort services by response time (descending)
            services_by_latency = sorted(
                services, 
                key=lambda x: x.get('avg_response_time', 0), 
                reverse=True
            )
            
            # Identify relevant nodes based on error rate and latency
            relevant_nodes = []
            
            # Add services with high error rates
            for service in services_by_error:
                if service.get('error_rate', 0) > 0 and len(relevant_nodes) < max_relevant_nodes:
                    relevant_nodes.append({
                        'service_name': service.get('name', 'unknown'),
                        'service_type': service.get('type', 'unknown'),
                        'error_rate': service.get('error_rate', 0),
                        'latency': service.get('avg_response_time', 0),
                        'request_count': service.get('request_count', 0),
                        'reason': f"High error rate: {service.get('error_rate', 0):.2f}%"
                    })
            
            # Add services with high latency (if not already added)
            for service in services_by_latency:
                if service.get('avg_response_time', 0) > 0:
                    service_name = service.get('name', 'unknown')
                    if not any(node['service_name'] == service_name for node in relevant_nodes) and len(relevant_nodes) < max_relevant_nodes:
                        relevant_nodes.append({
                            'service_name': service_name,
                            'service_type': service.get('type', 'unknown'),
                            'error_rate': service.get('error_rate', 0),
                            'latency': service.get('avg_response_time', 0),
                            'request_count': service.get('request_count', 0),
                            'reason': f"High latency: {service.get('avg_response_time', 0):.2f}ms"
                        })
            
            return {
                'relevant_nodes': relevant_nodes,
                'root_service': service_graph.get('root_service', {}),
                'total_services': service_graph.get('total_services', 0),
                'total_requests': service_graph.get('total_requests', 0),
                'overall_error_rate': service_graph.get('overall_error_rate', 0)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing service graph: {e}")
            return {
                "error": str(e),
                "relevant_nodes": []
            }

# Create a singleton instance
xray_tool = XRayServiceGraphTool(region_name="ap-southeast-1")  # Default to ap-southeast-1

@tool
def get_xray_service_graph(input_str: str) -> str:
    """
    Get the AWS X-Ray service graph for the last X minutes in the specified region.
    
    Args:
        input_str: String containing minutes and optionally region in format "minutes,region" (e.g., "360,us-west-2")
                  If no region is specified, ap-southeast-1 will be used as default.
        
    Returns:
        JSON string containing the service graph data
    """
    try:
        # Parse input
        parts = input_str.strip().split(',')
        minutes = int(parts[0].strip())
        region = parts[1].strip() if len(parts) > 1 else "ap-southeast-1"
        
        if minutes <= 0:
            minutes = 15
        
        # Limit to 6 hours (360 minutes) maximum
        if minutes > 360:
            minutes = 360
        
        # Create a tool instance with the specified region if different from default
        if region != xray_tool.region_name:
            tool_instance = XRayServiceGraphTool(region_name=region)
        else:
            tool_instance = xray_tool
        
        # Get the service graph
        service_graph = tool_instance.get_service_graph(minutes=minutes)
        
        # Return as JSON string
        return json.dumps(service_graph, default=str)
        
    except Exception as e:
        return json.dumps({
            "error": f"Error getting X-Ray service graph: {str(e)}",
            "service_graph": {},
            "services": [],
            "edges": []
        })

@tool
def analyze_xray_service_graph(input_str: str) -> str:
    """
    Get and analyze the AWS X-Ray service graph for the last X minutes in the specified region.
    
    Args:
        input_str: String containing minutes and optionally region in format "minutes,region" (e.g., "360,us-west-2")
                  If no region is specified, ap-southeast-1 will be used as default.
        
    Returns:
        JSON string containing the service graph analysis
    """
    try:
        # Parse input
        parts = input_str.strip().split(',')
        minutes = int(parts[0].strip())
        region = parts[1].strip() if len(parts) > 1 else "ap-southeast-1"
        
        if minutes <= 0:
            minutes = 15
        
        # Limit to 6 hours (360 minutes) maximum
        if minutes > 360:
            minutes = 360
        
        # Create a tool instance with the specified region if different from default
        if region != xray_tool.region_name:
            tool_instance = XRayServiceGraphTool(region_name=region)
        else:
            tool_instance = xray_tool
        
        # Get the service graph
        service_graph = tool_instance.get_service_graph(minutes=minutes)
        
        # Analyze the service graph
        analysis = tool_instance.analyze_service_graph(service_graph, max_relevant_nodes=3)
        
        # Combine results
        result = {
            'service_graph': {
                'root_service_name': service_graph.get('root_service', {}).get('name', 'unknown'),
                'root_service_type': service_graph.get('root_service', {}).get('type', 'unknown'),
                'total_services': service_graph.get('total_services', 0),
                'total_requests': service_graph.get('total_requests', 0),
                'error_rate': service_graph.get('overall_error_rate', 0)
            },
            'relevant_nodes': analysis.get('relevant_nodes', []),
            'region': service_graph.get('region', 'unknown'),
            'time_range': {
                'start_time': service_graph.get('start_time'),
                'end_time': service_graph.get('end_time'),
                'minutes': minutes
            }
        }
        
        # Return as JSON string
        return json.dumps(result, default=str)
        
    except Exception as e:
        return json.dumps({
            "error": f"Error analyzing X-Ray service graph: {str(e)}",
            "service_graph": {},
            "relevant_nodes": []
        })
