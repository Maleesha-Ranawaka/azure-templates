from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

# stateless_http=True is required when running multiple replicas behind a
# load balancer / ingress, because MCP sessions are otherwise held in memory
# on a single instance.
mcp = FastMCP("fastmcp-server", stateless_http=True)


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


# Health endpoint for Kubernetes readiness/liveness probes.
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp/")
