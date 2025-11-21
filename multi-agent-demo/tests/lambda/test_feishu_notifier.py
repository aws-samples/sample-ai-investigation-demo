#!/usr/bin/env python3
"""Test script for Feishu notifier Lambda function"""

import boto3
import json

def get_lambda_function_name():
    """Get the actual Lambda function name from CloudFormation outputs"""
    cf_client = boto3.client('cloudformation')
    
    try:
        response = cf_client.describe_stacks(StackName='AIOpsStack')
        outputs = response['Stacks'][0]['Outputs']
        
        for output in outputs:
            if output['OutputKey'] == 'FeishuNotifierArn':
                # Extract function name from ARN
                arn = output['OutputValue']
                return arn.split(':')[-1]
    except Exception as e:
        print(f"Error getting function name from CloudFormation: {e}")
        return None

def test_feishu_notifier():
    """Test the Feishu notifier Lambda function"""
    
    # Get actual function name
    function_name = get_lambda_function_name()
    if not function_name:
        print("❌ Could not find Lambda function name")
        return
    
    print(f"Testing function: {function_name}")
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda')
    
    # Test payload
    test_payload = {
        "title": "🚨 AIOps Investigation Alert",
        "message": """**Investigation Started**
        
**Alarm:** High CPU Utilization
**Instance:** i-1234567890abcdef0
**Threshold:** 80%
**Current Value:** 95%
**Status:** ALARM

Investigation workflow has been initiated. Root cause analysis in progress...
        """
    }
    
    try:
        # Invoke the Lambda function
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        # Parse response
        result = json.loads(response['Payload'].read())
        print("Lambda Response:", result)
        
        if response['StatusCode'] == 200:
            print("✅ Feishu notification sent successfully!")
        else:
            print("❌ Failed to send notification")
            
    except Exception as e:
        print(f"❌ Error testing Feishu notifier: {e}")

if __name__ == "__main__":
    test_feishu_notifier()
