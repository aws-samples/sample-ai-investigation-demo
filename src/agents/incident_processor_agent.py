"""
Incident Processor Agent - Final agent in the AIOps workflow
Responsible for creating incident tickets and providing remediation recommendations
"""

import json
import random
import string
import sys
import os
from langchain_core.tools import tool
from langchain_core.messages import AIMessage

# Add the parent directory to the path so we can import modules from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from util import COMMON_TOOLS, create_prompt_template, create_agent_executor, get_bedrock_model
from agents.agent import Agent

class IncidentProcessorAgent(Agent):
    """Incident Processor Agent for creating tickets and providing remediation recommendations"""
    
    def __init__(self):
        """Initialize the Incident Processor Agent"""
        super().__init__("Incident Processor Agent")
        self.prompt = create_prompt_template("Incident Processing", INCIDENT_PROCESSOR_INSTRUCTIONS)
        self.agent_executor = create_agent_executor(self.model, INCIDENT_PROCESSOR_TOOLS, self.prompt)
    
    def process(self, input_data):
        """
        Process the input data and return incident processing results
        
        Args:
            input_data: Input data containing incident information
            
        Returns:
            Dict containing incident processing results
        """
        try:
            result = self.agent_executor.invoke({
                "input": f"Process this incident and provide remediation recommendations. Make sure to create an incident ticket using the create_incident_ticket tool:\n\n{input_data}"
            })
            
            return result["output"]
        except Exception as e:
            # If there's an error with tool calling, provide a fallback response
            if "validation error" in str(e).lower() and "create_incident_ticket" in str(e):
                # Extract basic information for manual ticket creation
                import re
                
                # Try to extract title from the error message
                title_match = re.search(r"'title': '([^']*)'", str(e))
                title = title_match.group(1) if title_match else "CloudWatch Alert Incident"
                
                # Clean up title if it contains JSON
                if title.startswith('\n{') and title.endswith('}\n'):
                    try:
                        title_data = json.loads(title.strip())
                        if isinstance(title_data, dict) and 'title' in title_data:
                            title = title_data['title']
                    except:
                        title = "CloudWatch Alert Incident"
                
                # Create ticket manually using the tool function directly
                ticket_result = create_incident_ticket(
                    title=title,
                    description=f"Incident created from CloudWatch alert. Original input: {input_data[:500]}...",
                    severity="medium"
                )
                
                return f"Incident processed with manual ticket creation due to tool error:\n\n{ticket_result}\n\nRecommendations:\n- Review the alert details\n- Check affected resources\n- Implement appropriate remediation steps\n- Monitor for resolution"
            else:
                raise e

# Incident processor specific tools
@tool
def create_incident_ticket(title: str, description: str = "", severity: str = "medium", affected_resources: str = None) -> str:
    """Create an incident ticket in the ticketing system.
    This is a simulation of creating a ticket in a real system.
    
    Args:
        title: The title of the incident (required)
        description: Detailed description of the incident (optional, defaults to empty string)
        severity: Incident severity - must be one of: low, medium, high, critical (optional, defaults to medium)
        affected_resources: Comma-separated list of affected resource IDs (optional)
    
    Returns:
        JSON string containing the created ticket information
    """
    # In a real implementation, this would connect to a ticketing system API
    # For demo purposes, we'll just return a simulated response
    
    # Handle case where title might contain JSON data
    if isinstance(title, str) and title.startswith('\n{') and title.endswith('}\n'):
        try:
            # Try to parse the title as JSON and extract the actual title
            title_data = json.loads(title.strip())
            if isinstance(title_data, dict) and 'title' in title_data:
                actual_title = title_data['title']
                # Use other fields from the JSON if description is empty
                if not description and 'description' in title_data:
                    description = title_data['description']
                if severity == "medium" and 'severity' in title_data:
                    severity = title_data['severity']
                title = actual_title
        except json.JSONDecodeError:
            # If parsing fails, use the title as-is
            pass
    
    # Handle case where title might be a dict (shouldn't happen but let's be safe)
    if isinstance(title, dict):
        if 'title' in title:
            actual_title = title['title']
            if not description and 'description' in title:
                description = title['description']
            if severity == "medium" and 'severity' in title:
                severity = title['severity']
            title = actual_title
        else:
            title = str(title)
    
    # Ensure we have a description
    if not description:
        description = f"Incident ticket created for: {title}"
    
    # Ensure title is a string
    if not isinstance(title, str):
        title = str(title)
    
    valid_severities = ["low", "medium", "high", "critical"]
    if severity.lower() not in valid_severities:
        return f"Error: Invalid severity '{severity}'. Must be one of: {', '.join(valid_severities)}"
    
    # Generate a random ticket ID
    ticket_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    response = {
        "ticket_id": f"INC-{ticket_id}",
        "title": title,
        "description": description,
        "severity": severity.lower(),
        "affected_resources": affected_resources.split(",") if affected_resources else [],
        "status": "created",
        "created_at": "2025-05-22T06:00:00Z"
    }
    
    return json.dumps(response, indent=2)
    """Create an incident ticket in the ticketing system.
    This is a simulation of creating a ticket in a real system.
    
    Args:
        title: The title of the incident (required)
        description: Detailed description of the incident (optional, defaults to empty string)
        severity: Incident severity - must be one of: low, medium, high, critical (optional, defaults to medium)
        affected_resources: Comma-separated list of affected resource IDs (optional)
    
    Returns:
        JSON string containing the created ticket information
    """
    # Debug logging to see what parameters are being passed
    print(f"DEBUG: create_incident_ticket called with:")
    print(f"  title: {repr(title)}")
    print(f"  description: {repr(description)}")
    print(f"  severity: {repr(severity)}")
    print(f"  affected_resources: {repr(affected_resources)}")
    
    # In a real implementation, this would connect to a ticketing system API
    # For demo purposes, we'll just return a simulated response
    
    # Handle case where title might contain JSON data
    if isinstance(title, str) and title.startswith('\n{') and title.endswith('}\n'):
        try:
            # Try to parse the title as JSON and extract the actual title
            title_data = json.loads(title.strip())
            if isinstance(title_data, dict) and 'title' in title_data:
                actual_title = title_data['title']
                # Use other fields from the JSON if description is empty
                if not description and 'description' in title_data:
                    description = title_data['description']
                if severity == "medium" and 'severity' in title_data:
                    severity = title_data['severity']
                title = actual_title
                print(f"DEBUG: Parsed JSON title, extracted: {repr(title)}")
        except json.JSONDecodeError as e:
            # If parsing fails, use the title as-is
            print(f"DEBUG: Failed to parse JSON title: {e}")
            pass
    
    # Handle case where title might be a dict (shouldn't happen but let's be safe)
    if isinstance(title, dict):
        if 'title' in title:
            actual_title = title['title']
            if not description and 'description' in title:
                description = title['description']
            if severity == "medium" and 'severity' in title:
                severity = title['severity']
            title = actual_title
        else:
            title = str(title)
    
    # Ensure we have a description
    if not description:
        description = f"Incident ticket created for: {title}"
    
    # Ensure title is a string
    if not isinstance(title, str):
        title = str(title)
    
    valid_severities = ["low", "medium", "high", "critical"]
    if severity.lower() not in valid_severities:
        return f"Error: Invalid severity '{severity}'. Must be one of: {', '.join(valid_severities)}"
    
    # Generate a random ticket ID
    ticket_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    response = {
        "ticket_id": f"INC-{ticket_id}",
        "title": title,
        "description": description,
        "severity": severity.lower(),
        "affected_resources": affected_resources.split(",") if affected_resources else [],
        "status": "created",
        "created_at": "2025-05-22T06:00:00Z"
    }
    
    return json.dumps(response, indent=2)

# Incident processor role-specific instructions
INCIDENT_PROCESSOR_INSTRUCTIONS = '''Your role is to process the CloudWatch alert as an incident based on the collected information. You should:
1. Determine the severity and impact of the incident
2. Create an incident ticket with appropriate details using the create_incident_ticket tool
3. Recommend immediate remediation steps
4. Suggest long-term preventive measures
5. Provide a final response summarizing the incident, its cause, and recommended actions

When creating incident tickets, always provide:
- title: A clear, concise title describing the incident
- description: A detailed description of the incident, its impact, and context
- severity: One of "low", "medium", "high", or "critical"
- affected_resources: Comma-separated list of affected resource IDs (if known)

For EC2 instances with high CPU:
- Recommend scaling options (vertical or horizontal)
- Suggest process optimization or termination of unnecessary processes
- Recommend monitoring and auto-scaling configurations

For RDS instances with storage issues:
- Recommend immediate cleanup actions (temporary files, logs)
- Suggest storage scaling options
- Recommend data archiving or purging strategies

For API Gateway with high error rates:
- Recommend backend service scaling or optimization
- Suggest client throttling or rate limiting
- Recommend error handling improvements

You are the final agent in the workflow and should provide a comprehensive response that includes:
1. A summary of the alert and affected resources
2. The identified root cause
3. Immediate remediation steps
4. Long-term recommendations
5. Incident ticket details (created using the create_incident_ticket tool)

Always use the create_incident_ticket tool to create a ticket as part of your response.'''

# Incident processor tools
INCIDENT_PROCESSOR_TOOLS = COMMON_TOOLS.copy()
INCIDENT_PROCESSOR_TOOLS.append(create_incident_ticket)
