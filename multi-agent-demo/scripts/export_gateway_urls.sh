#!/bin/bash

# Export gateway URLs and queue URL from CDK stack outputs
# Usage: source scripts/export_gateway_urls.sh

STACK_NAME="${STACK_NAME_PREFIX:-aiops-demo}-main"
REGION="${AWS_REGION:-ap-southeast-1}"

echo "Getting URLs from stack: $STACK_NAME"

# Get gateway ARN from stack outputs
GATEWAY_ARN=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query "Stacks[0].Outputs[?OutputKey=='AgentCoreGatewayArn'].OutputValue" \
  --output text)

if [ -z "$GATEWAY_ARN" ]; then
  echo "❌ Error: Could not find AgentCoreGatewayArn in stack outputs"
  exit 1
fi

# Get queue URL from stack outputs
QUEUE_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query "Stacks[0].Outputs[?OutputKey=='InvestigationQueueUrl'].OutputValue" \
  --output text)

# Extract gateway identifier from ARN
# ARN format: arn:aws:bedrock-agentcore:region:account:gateway/gateway-id
GATEWAY_ID=$(echo $GATEWAY_ARN | awk -F'/' '{print $2}')

# Construct gateway URL
GATEWAY_URL="https://${GATEWAY_ID}.gateway.bedrock-agentcore.${REGION}.amazonaws.com/mcp"

echo "✅ Gateway ID: $GATEWAY_ID"
echo "✅ Gateway URL: $GATEWAY_URL"
echo "✅ Queue URL: $QUEUE_URL"
echo ""

# Export environment variables
export NOTIFICATION_GATEWAY_URL="$GATEWAY_URL"
export INVESTIGATION_QUEUE_URL="$QUEUE_URL"
export AWS_REGION="$REGION"

echo "Exported environment variables:"
echo "  NOTIFICATION_GATEWAY_URL=$NOTIFICATION_GATEWAY_URL"
echo "  INVESTIGATION_QUEUE_URL=$INVESTIGATION_QUEUE_URL"
echo "  AWS_REGION=$AWS_REGION"
echo ""
echo "Run your test with:"
echo "  python tests/brain/test_local_alarm.py"
