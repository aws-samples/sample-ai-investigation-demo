#!/usr/bin/env python3
"""
Test script for the domain_bot_node
"""

import sys
import os
import json

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nodes.domain_bot_node import domain_bot_node
from langchain_core.messages import HumanMessage

# Import constants
from constants import ContextKeys, AnalysisKeys

def test_domain_bot_with_rds_scenario():
    """
    Test the domain_bot_node with RDS database scenario
    """
    print(f"\n{'='*80}")
    print(f"TESTING DOMAIN BOT NODE WITH RDS SCENARIO")
    print(f"{'='*80}")
    
    # Sample decision data for RDS scenario
    decision_data = {
        "decision": {
            "alert_type": "RDSConnectionFailures",
            "resource_type": "AWS::RDS::DBInstance",
            "severity": "High",
            "recommended_path": "resource",
            "reasoning": "Database connection failures require domain expertise and resource analysis"
        },
        "alarm_summary": {
            "alert_type": "RDSConnectionFailures",
            "resource_type": "AWS::RDS::DBInstance",
            "severity": "High"
        }
    }
    
    # Context for RDS scenario
    sample_context = {
        ContextKeys.ALARM_ANALYSIS: {
            "identified_alarm_types": ["RDSConnectionFailures"],
            "severity": "High",
            "extracted_info": {
                "alarm_name": "RDS-Connection-Failures",
                "alarm_start_time": "2025-06-10T02:05:00Z",
                "related_resources": [
                    {
                        "resource_id": "prod-postgres-db",
                        "resource_type": "AWS::RDS::DBInstance",
                        "resource_name": "Production PostgreSQL Database"
                    }
                ],
                "region": "us-east-1",
                "account_id": "123456789012"
            },
            "possible_causes": [
                "Connection pool exhaustion",
                "Database instance overload",
                "Network connectivity issues"
            ]
        },
        ContextKeys.INITIAL_DECISION: {
            "alert_type": "RDSConnectionFailures",
            "resource_type": "AWS::RDS::DBInstance",
            "severity": "High",
            "recommended_path": "resource"
        }
    }
    
    # Create initial state
    initial_state = {
        "messages": [HumanMessage(content=json.dumps(decision_data))],
        "context": sample_context
    }
    
    # Call the domain_bot_node
    print("\nCalling domain_bot_node...")
    result = domain_bot_node(initial_state)
    
    # Print the result
    print("\nRESULT:")
    print(f"\nMessages: {result['messages'][0].content[:500]}...")
    print(f"\nContext keys: {list(result['context'].keys())}")
    
    # Verify domain analysis context
    if 'domain_analysis' in result['context']:
        domain_analysis = result['context']['domain_analysis']
        print("\nVERIFICATION:")
        print(f"- Domain analysis keys: {list(domain_analysis.keys())}")
        print(f"- Identified resources: {domain_analysis.get('identified_resources', [])}")
        print(f"- Potential issues: {domain_analysis.get('potential_issues', [])}")
        print(f"- Raw analysis available: {'raw_analysis' in domain_analysis}")
    
    return result

def test_domain_bot_with_ec2_scenario():
    """
    Test the domain_bot_node with EC2 high CPU scenario
    """
    print(f"\n{'='*80}")
    print(f"TESTING DOMAIN BOT NODE WITH EC2 HIGH CPU SCENARIO")
    print(f"{'='*80}")
    
    # Sample decision data for EC2 scenario
    decision_data = {
        "decision": {
            "alert_type": "EC2HighCPU",
            "resource_type": "AWS::EC2::Instance",
            "severity": "Medium",
            "recommended_path": "resource",
            "reasoning": "High CPU utilization requires domain analysis to understand workload patterns"
        },
        "alarm_summary": {
            "alert_type": "EC2HighCPU",
            "resource_type": "AWS::EC2::Instance",
            "severity": "Medium"
        }
    }
    
    # Context for EC2 scenario
    sample_context = {
        ContextKeys.ALARM_ANALYSIS: {
            "identified_alarm_types": ["EC2HighCPU"],
            "severity": "Medium",
            "extracted_info": {
                "alarm_name": "High-CPU-Alarm",
                "alarm_start_time": "2025-05-22T06:15:00Z",
                "related_resources": [
                    {
                        "resource_id": "i-0515355a75c579ece",
                        "resource_type": "AWS::EC2::Instance",
                        "resource_name": "Web Server Instance"
                    }
                ],
                "region": "ap-southeast-1",
                "account_id": "613477150601"
            },
            "possible_causes": [
                "High application load",
                "Inefficient processes",
                "Memory pressure causing CPU spikes"
            ]
        },
        ContextKeys.INITIAL_DECISION: {
            "alert_type": "EC2HighCPU",
            "resource_type": "AWS::EC2::Instance",
            "severity": "Medium",
            "recommended_path": "resource"
        }
    }
    
    # Create initial state
    initial_state = {
        "messages": [HumanMessage(content=json.dumps(decision_data))],
        "context": sample_context
    }
    
    # Call the domain_bot_node
    print("\nCalling domain_bot_node...")
    result = domain_bot_node(initial_state)
    
    # Print the result
    print("\nRESULT:")
    print(f"\nMessages length: {len(result['messages'][0].content)} characters")
    print(f"Context keys: {list(result['context'].keys())}")
    
    return result

def test_domain_bot_with_s3_scenario():
    """
    Test the domain_bot_node with S3 access errors scenario
    """
    print(f"\n{'='*80}")
    print(f"TESTING DOMAIN BOT NODE WITH S3 ACCESS ERRORS")
    print(f"{'='*80}")
    
    # Sample decision data for S3 scenario
    decision_data = {
        "decision": {
            "alert_type": "S3AccessErrors",
            "resource_type": "AWS::S3::Bucket",
            "severity": "Medium",
            "recommended_path": "resource",
            "reasoning": "S3 access errors require domain expertise to analyze permissions and policies"
        },
        "alarm_summary": {
            "alert_type": "S3AccessErrors",
            "resource_type": "AWS::S3::Bucket",
            "severity": "Medium"
        }
    }
    
    # Context for S3 scenario
    sample_context = {
        ContextKeys.ALARM_ANALYSIS: {
            "identified_alarm_types": ["S3AccessErrors"],
            "severity": "Medium",
            "extracted_info": {
                "alarm_name": "S3-Access-Denied-Errors",
                "alarm_start_time": "2025-06-10T04:30:00Z",
                "related_resources": [
                    {
                        "resource_id": "my-app-data-bucket",
                        "resource_type": "AWS::S3::Bucket",
                        "resource_name": "Application Data Bucket"
                    }
                ],
                "region": "us-west-2",
                "account_id": "123456789012"
            },
            "possible_causes": [
                "IAM policy changes",
                "Bucket policy restrictions",
                "Cross-account access issues"
            ]
        },
        ContextKeys.INITIAL_DECISION: {
            "alert_type": "S3AccessErrors",
            "resource_type": "AWS::S3::Bucket",
            "severity": "Medium",
            "recommended_path": "resource"
        }
    }
    
    # Create initial state
    initial_state = {
        "messages": [HumanMessage(content=json.dumps(decision_data))],
        "context": sample_context
    }
    
    # Call the domain_bot_node
    print("\nCalling domain_bot_node...")
    result = domain_bot_node(initial_state)
    
    # Print the result
    print("\nRESULT:")
    print(f"\nMessages length: {len(result['messages'][0].content)} characters")
    print(f"Context keys: {list(result['context'].keys())}")
    
    return result

def main():
    """Main function to run all tests"""
    print("Running domain_bot_node tests...")
    
    # Test 1: RDS scenario
    test_domain_bot_with_rds_scenario()
    
    # Test 2: EC2 scenario
    test_domain_bot_with_ec2_scenario()
    
    # Test 3: S3 scenario
    test_domain_bot_with_s3_scenario()
    
    print(f"\n{'='*80}")
    print("ALL DOMAIN BOT TESTS COMPLETED")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
