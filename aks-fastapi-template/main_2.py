import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Security
from fastapi_azure_auth import MultiTenantAzureAuthorizationCodeBearer

# Backend API App Registration (client) ID — used to validate the token's
# audience (aud) claim. Injected as an env var from vars.yml.
APP_CLIENT_ID = os.environ["APP_CLIENT_ID"]
# SPA / Swagger-UI App Registration (client) ID — prefills the docs login button.
OPENAPI_CLIENT_ID = os.environ.get("OPENAPI_CLIENT_ID", "")

# Multi-tenant scheme: accepts users from ANY Azure AD tenant.
# validate_iss=False = don't restrict to a specific tenant's issuer.
azure_scheme = MultiTenantAzureAuthorizationCodeBearer(
    app_client_id=APP_CLIENT_ID,
    scopes={
        f"api://{APP_CLIENT_ID}/user_impersonation": "user_impersonation",
    },
    validate_iss=False,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load Azure AD's signing keys once at startup so tokens can be validated.
    await azure_scheme.openid_config.load_config()
    yield


app = FastAPI(
    lifespan=lifespan,
    swagger_ui_oauth2_redirect_url="/oauth2-redirect",
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": OPENAPI_CLIENT_ID,
    },
)


# PUBLIC — no auth. Kubernetes health probes hit this, so it must stay open.
@app.get("/health")
def health():
    return {"status": "healthy"}


# PROTECTED — requires a valid Azure AD bearer token with the user_impersonation scope.
@app.get("/", dependencies=[Security(azure_scheme, scopes=["user_impersonation"])])
def root():
    return {"message": "Hello from FastAPI on AKS"}
