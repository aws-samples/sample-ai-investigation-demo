#!/bin/bash

# Set environment variables (update these with your values)
export AGENT_RUNTIME_ARN="arn:aws:bedrock-agentcore:REGION:ACCOUNT:agent-runtime/RUNTIME_ID"
export INVESTIGATIONS_TABLE="aiops-investigations"
export CONTEXT_TABLE="aiops-investigation-context"
export AGENTCORE_LOG_GROUP="/aws/bedrock-agentcore/runtime"
export AWS_REGION="ap-southeast-1"

# Install dependencies if needed
if [ ! -d ".streamlit_venv" ]; then
    python3 -m venv .streamlit_venv
    source .streamlit_venv/bin/activate
    pip install -r streamlit_requirements.txt
else
    source .streamlit_venv/bin/activate
fi

# Run Streamlit
streamlit run streamlit_app.py
