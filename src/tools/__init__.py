"""
Tools package for AWS resource attribute collection

This package provides tools for collecting detailed attributes and metrics
from various AWS resources for use in AIOps workflows.
"""

from .resource_attributes_collector import ResourceAttributesCollector
from .resource_utils import (
    collect_multiple_resource_attributes,
    get_resource_summary,
    extract_resource_arns_from_text,
    format_resource_collection_for_display
)
from .cloudtrail_collector import CloudTrailCollector
from .cloudtrail_utils import (
    collect_events_for_incident,
    analyze_incident_events,
    extract_resource_arns_from_context,
    format_cloudtrail_analysis_for_display,
    generate_cloudtrail_recommendations
)

__all__ = [
    'ResourceAttributesCollector',
    'collect_multiple_resource_attributes',
    'get_resource_summary',
    'extract_resource_arns_from_text',
    'format_resource_collection_for_display',
    'CloudTrailCollector',
    'collect_events_for_incident',
    'analyze_incident_events',
    'extract_resource_arns_from_context',
    'format_cloudtrail_analysis_for_display',
    'generate_cloudtrail_recommendations'
]
