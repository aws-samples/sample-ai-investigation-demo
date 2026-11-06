"""Fetch an OAuth2 client_credentials token from the Cognito domain used by the gateway.

Required environment variables:
  COGNITO_TOKEN_URL      e.g. https://<domain>.auth.<region>.amazoncognito.com/oauth2/token
  COGNITO_CLIENT_ID
  COGNITO_CLIENT_SECRET
Optional:
  COGNITO_SCOPE          e.g. <resource-server-id>/read
"""
import os
import sys

import requests


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(f"Missing required environment variable: {name}")
    return value


token_url = require_env("COGNITO_TOKEN_URL")
data = {
    "grant_type": "client_credentials",
    "client_id": require_env("COGNITO_CLIENT_ID"),
    "client_secret": require_env("COGNITO_CLIENT_SECRET"),
}
scope = os.getenv("COGNITO_SCOPE")
if scope:
    data["scope"] = scope

response = requests.post(
    token_url,
    data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    timeout=30,
)
response.raise_for_status()
# Avoid printing the token itself; just confirm success.
body = response.json()
print(f"Token acquired: type={body.get('token_type')} expires_in={body.get('expires_in')}")
