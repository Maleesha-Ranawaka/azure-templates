import os

from fastmcp import FastMCP
from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier
from starlette.requests import Request
from starlette.responses import PlainTextResponse

# Backend MCP App Registration (client) ID — the token audience (api://<client_id>).
# Injected as an env var from vars.yml.
APP_CLIENT_ID = os.environ["APP_CLIENT_ID"]
# Public URL clients reach this server on (advertised in the OAuth metadata).
BASE_URL = os.environ["BASE_URL"]

# Multi-tenant: validate bearer tokens issued by ANY Azure AD tenant.
# Signing keys come from Azure's COMMON (multi-tenant) JWKS endpoint. We verify
# the signature, audience and scope but do not pin a single tenant's issuer —
# this mirrors the FastAPI validate_iss=False multi-tenant posture.
verifier = JWTVerifier(
    jwks_uri="https://login.microsoftonline.com/common/discovery/v2.0/keys",
    audience=f"api://{APP_CLIENT_ID}",
    required_scopes=["user_impersonation"],
)

# RemoteAuthProvider = this server is a pure resource server: it validates
# pre-issued tokens and delegates login to Azure AD. No client secret needed.
auth = RemoteAuthProvider(
    token_verifier=verifier,
    authorization_servers=["https://login.microsoftonline.com/organizations/v2.0"],
    base_url=BASE_URL,
)

# stateless_http=True is required for multiple replicas behind the ingress.
mcp = FastMCP("fastmcp-server", stateless_http=True, auth=auth)


# PROTECTED — callers must present a valid Azure AD bearer token.
@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


# PUBLIC — custom routes are not gated by MCP auth. Used by Kubernetes probes.
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp/")
