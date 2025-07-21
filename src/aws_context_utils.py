"""
AWS Context Utilities

This module provides utilities for extracting and managing AWS context information
like region and account_id from various AWS resources and alarm data.
"""

import re
import json
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

def extract_aws_context_from_alarm_data(alarm_data: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract AWS region and account_id from alarm analysis data
    
    Args:
        alarm_data: Alarm analysis data containing alarm information
        
    Returns:
        Tuple of (region, account_id) or (None, None) if not found
    """
    try:
        region = None
        account_id = None
        
        # Try to extract from alarm_arn if present
        alarm_arn = alarm_data.get('alarm_arn', '')
        if alarm_arn:
            region, account_id = extract_aws_context_from_arn(alarm_arn)
            if region and account_id:
                logger.info(f"Extracted AWS context from alarm ARN: region={region}, account_id={account_id}")
                return region, account_id
        
        # Try to extract from raw alarm text/content
        raw_content = str(alarm_data)
        
        # Look for alarm ARN pattern in the content
        arn_pattern = r'arn:aws:cloudwatch:([^:]+):(\d+):alarm:'
        match = re.search(arn_pattern, raw_content)
        if match:
            region = match.group(1)
            account_id = match.group(2)
            logger.info(f"Extracted AWS context from alarm content: region={region}, account_id={account_id}")
            return region, account_id
        
        # Look for AWS Account pattern
        account_pattern = r'AWS Account:\s*(\d+)'
        account_match = re.search(account_pattern, raw_content)
        if account_match:
            account_id = account_match.group(1)
        
        # Look for region in console URL
        region_pattern = r'region=([a-z0-9-]+)'
        region_match = re.search(region_pattern, raw_content)
        if region_match:
            region = region_match.group(1)
        
        # Look for region in alarm description or other fields
        if not region:
            region_patterns = [
                r'in the ([a-z0-9-]+) region',
                r'region[:\s]+([a-z0-9-]+)',
                r'([a-z]{2}-[a-z]+-\d+)'  # Generic AWS region pattern
            ]
            for pattern in region_patterns:
                match = re.search(pattern, raw_content, re.IGNORECASE)
                if match:
                    potential_region = match.group(1)
                    if is_valid_aws_region(potential_region):
                        region = potential_region
                        break
        
        if region or account_id:
            logger.info(f"Extracted AWS context from alarm data: region={region}, account_id={account_id}")
            return region, account_id
        
        logger.warning("Could not extract AWS context from alarm data")
        return None, None
        
    except Exception as e:
        logger.error(f"Error extracting AWS context from alarm data: {e}")
        return None, None

def extract_aws_context_from_arn(arn: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract AWS region and account_id from an ARN
    
    Args:
        arn: AWS ARN string
        
    Returns:
        Tuple of (region, account_id) or (None, None) if not found
    """
    try:
        if not arn or not arn.startswith('arn:aws:'):
            return None, None
        
        # ARN format: arn:aws:service:region:account-id:resource
        parts = arn.split(':')
        if len(parts) >= 5:
            region = parts[3] if parts[3] else None
            account_id = parts[4] if parts[4] else None
            return region, account_id
        
        return None, None
        
    except Exception as e:
        logger.error(f"Error extracting AWS context from ARN {arn}: {e}")
        return None, None

def is_valid_aws_region(region: str) -> bool:
    """
    Check if a string is a valid AWS region format
    
    Args:
        region: Potential AWS region string
        
    Returns:
        True if it looks like a valid AWS region
    """
    if not region:
        return False
    
    # AWS region pattern: us-east-1, eu-west-1, ap-southeast-1, etc.
    region_pattern = r'^[a-z]{2}-[a-z]+-\d+$'
    return bool(re.match(region_pattern, region))

def get_aws_context_from_state(state: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Get AWS context (region, account_id) from workflow state
    
    Args:
        state: Workflow state containing context
        
    Returns:
        Tuple of (region, account_id) or (None, None) if not found
    """
    try:
        context = state.get('context', {})
        
        # First, try to get from context directly
        region = context.get('region')
        account_id = context.get('account_id')
        
        if region and account_id:
            return region, account_id
        
        # If not in context, try to extract from alarm_analysis
        alarm_analysis = context.get('alarm_analysis', {})
        if alarm_analysis:
            extracted_region, extracted_account_id = extract_aws_context_from_alarm_data(alarm_analysis)
            if extracted_region or extracted_account_id:
                return extracted_region or region, extracted_account_id or account_id
        
        return region, account_id
        
    except Exception as e:
        logger.error(f"Error getting AWS context from state: {e}")
        return None, None

def update_context_with_aws_info(context: Dict, region: str = None, account_id: str = None) -> Dict:
    """
    Update context with AWS region and account_id information
    
    Args:
        context: Context dictionary to update
        region: AWS region
        account_id: AWS account ID
        
    Returns:
        Updated context dictionary
    """
    try:
        if region:
            context['region'] = region
            logger.debug(f"Updated context with region: {region}")
        
        if account_id:
            context['account_id'] = account_id
            logger.debug(f"Updated context with account_id: {account_id}")
        
        return context
        
    except Exception as e:
        logger.error(f"Error updating context with AWS info: {e}")
        return context

def get_default_region() -> str:
    """
    Get default AWS region
    
    Returns:
        Default AWS region string
    """
    return 'us-east-1'

def format_aws_context_summary(region: str = None, account_id: str = None) -> str:
    """
    Format AWS context information for logging/display
    
    Args:
        region: AWS region
        account_id: AWS account ID
        
    Returns:
        Formatted string
    """
    parts = []
    if region:
        parts.append(f"Region: {region}")
    if account_id:
        parts.append(f"Account: {account_id}")
    
    if parts:
        return f"AWS Context - {', '.join(parts)}"
    else:
        return "AWS Context - Not available"
