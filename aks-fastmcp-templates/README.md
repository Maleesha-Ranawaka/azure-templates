# FastMCP on AKS — Deployment Template

A ready-to-use Azure DevOps template for deploying a **FastMCP** (Model Context Protocol) server to **Azure Kubernetes Service (AKS)** using **Azure Container Registry (ACR)**.

> **Audience:** DevOps engineers new to AKS pipelines. No prior experience with MCP or this template required.

---

## Table of Contents

1. [What is FastMCP?](#what-is-fastmcp)
2. [What This Template Does](#what-this-template-does)
3. [Folder Structure](#folder-structure)
4. [Prerequisites](#prerequisites)
5. [One-Time Azure Setup](#one-time-azure-setup)
6. [One-Time Azure DevOps Setup](#one-time-azure-devops-setup)
7. [How to Use This Template](#how-to-use-this-template)
8. [Understanding `vars.yml` — The Single Point of Change](#understanding-varsyml--the-single-point-of-change)
9. [Understanding `server.py` — The Application](#understanding-serverpy--the-application)
10. [How the Pipeline Works](#how-the-pipeline-works)
11. [How K8s Manifests Get Their Values](#how-k8s-manifests-get-their-values)
12. [Verifying Your Deployment](#verifying-your-deployment)
13. [Common Issues & Fixes](#common-issues--fixes)
14. [Customisation Guide](#customisation-guide)

---

## What is FastMCP?

FastMCP is a Python framework for building **MCP (Model Context Protocol) servers**. MCP is the standard that lets AI assistants (like Claude) call external tools and read external data in a controlled, permissioned way.

Unlike a normal web API (which serves browsers, mobile apps, or other services), an MCP server serves **AI models**. You expose:
- **Tools** — functions the AI can call (e.g. `get_customer_orders`, `search_docs`)
- **Resources** — data the AI can read
- **Prompts** — reusable prompt templates

An MCP server can run two ways:
- **stdio** — local, where the AI client launches the server itself (e.g. Claude Desktop on a laptop)
- **Streamable HTTP** — networked, so a remote AI client can reach it over the internet

**For AKS deployment we always use the HTTP transport**, because the server runs in the cluster and clients connect to it remotely.

> **Key point for beginners:** Once a FastMCP server runs over HTTP, it's just a Python web service listening on a port — structurally the same as any web app. That's why this template looks almost identical to a standard web-app deployment.

---

## What This Template Does

When you push code to the `main` branch, the pipeline automatically:

1. **Builds** a Docker image from your FastMCP server code
2. **Pushes** that image to your Azure Container Registry (ACR)
3. **Deploys** it to your AKS cluster as a Kubernetes Deployment, exposed via Service + Ingress

After deployment, AI clients connect to your server at `https://<your-host>/mcp/`.

The whole flow takes about 3–5 minutes.

---

## Folder Structure

```
fastmcp-aks-template/
├── vars.yml                     ← SINGLE POINT OF CHANGE (edit this only)
├── azure-pipelines.yml          ← Main pipeline (2 stages: build+push, deploy)
├── Dockerfile                   ← Defines the container image
├── server.py                    ← The FastMCP server (your tools live here)
├── requirements.txt             ← Python dependencies
├── pipelines/
│   ├── build-push.yml           ← Stage 1: Build + Push to ACR
│   └── deploy.yml               ← Stage 2: Deploy to AKS
└── k8s/
    ├── deployment.yaml          ← K8s Deployment (the actual pods)
    ├── service.yaml             ← K8s Service (internal load balancer)
    └── ingress.yaml             ← K8s Ingress (external access)
```

Only **three files are the actual application**: `server.py`, `requirements.txt`, and `Dockerfile`. Everything else is deployment machinery you can leave alone.

---

## Prerequisites

You need these things ready before using this template:

| Requirement | Why |
|---|---|
| **Azure subscription** with **Owner** or **Contributor** role | To create AKS, ACR, and grant permissions |
| **AKS cluster** already provisioned | Pipeline deploys *to* it, doesn't create it |
| **ACR** already provisioned | Pipeline pushes images *to* it |
| **Ingress controller** installed on AKS (e.g. NGINX) | For external traffic routing |
| **Azure DevOps project** | To run the pipeline |
| **Azure CLI** installed locally (optional) | For verification commands |

---

## One-Time Azure Setup

Run these commands once to prepare your Azure environment.

### 1. Allow AKS to pull from ACR

Without this, AKS can't download your images. Run:

```bash
az aks update \
  --name <aks-cluster-name> \
  --resource-group <aks-resource-group> \
  --attach-acr <acr-name>
```

This grants the AKS kubelet identity the `AcrPull` role on your ACR.

### 2. Install NGINX Ingress Controller (if not already installed)

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace
```

### 3. Get the Ingress public IP

```bash
kubectl get svc -n ingress-nginx
```

Copy the `EXTERNAL-IP` and create a DNS A-record pointing your domain (e.g. `mcp.example.com`) to it.

---

## One-Time Azure DevOps Setup

### 1. Create Service Connections

Go to **Project Settings → Service Connections → New service connection**.

| Connection Type | Name | Purpose |
|---|---|---|
| **Azure Resource Manager** | `sc-azure-prod` | For deploying to AKS |
| **Docker Registry** (Azure Container Registry) | `sc-acr-prod` | For pushing images to ACR |

> **Tip:** Use the same names that appear in `vars.yml` — or update `vars.yml` to match your names.

### 2. Install the "Replace Tokens" Extension

The deploy stage uses this to fill in placeholders in K8s manifests.

1. Go to [Azure DevOps Marketplace → Replace Tokens](https://marketplace.visualstudio.com/items?itemName=qetza.replacetokens)
2. Click **Get it free** and install it into your organisation

### 3. Create the Pipeline

1. Push this folder to a Git repository
2. In Azure DevOps go to **Pipelines → New Pipeline**
3. Select your repo
4. Select **Existing Azure Pipelines YAML file**
5. Pick `/azure-pipelines.yml`
6. Click **Run**

---

## How to Use This Template

### For a brand new MCP server

1. **Copy this folder** into your application repo (or fork it)
2. **Edit `server.py`** — replace the sample `add` tool with your real tools (see next section)
3. **Update `requirements.txt`** — add any libraries your tools need
4. **Edit `vars.yml`** — change the values to match your environment
5. **Commit and push to `main`** — pipeline runs automatically

### For an existing MCP server

Just drop in:
- `Dockerfile`
- `vars.yml`
- `azure-pipelines.yml`
- `pipelines/` folder
- `k8s/` folder

Make sure your server file is named `server.py` (or update the `Dockerfile` `CMD` to match), then edit `vars.yml` and push.

---

## Understanding `vars.yml` — The Single Point of Change

This is the **only file you should normally edit**. Every other file reads from these values.

```yaml
variables:

  # ── Application ──
  - name: appName              # Used as K8s deployment/service/ingress name
    value: 'fastmcp-server'
  - name: appPort              # Port the server listens on inside the container
    value: '8000'
  - name: mcpPath              # The URL path where the MCP endpoint is served
    value: '/mcp/'
  - name: replicaCount         # How many pod copies to run
    value: '2'

  # ── Azure / AKS ──
  - name: serviceConnection    # Azure DevOps service connection for AKS
    value: 'sc-azure-prod'
  - name: aksClusterName       # Name of your AKS cluster
    value: 'aks-myapp-prod'
  - name: aksResourceGroup     # Resource group containing AKS
    value: 'rg-aks-prod'
  - name: aksNamespace         # K8s namespace (created automatically if missing)
    value: 'fastmcp-prod'

  # ── Container Registry (ACR) ──
  - name: acrName              # Just the name, NOT the full URL
    value: 'acrmyappprod'
  - name: acrServiceConnection # Azure DevOps service connection for ACR
    value: 'sc-acr-prod'
  - name: imageRepository      # Image name (becomes acrname.azurecr.io/imageRepository)
    value: 'fastmcp-server'
  - name: imageTag             # Build ID = unique per pipeline run
    value: '$(Build.BuildId)'

  # ── Ingress ──
  - name: ingressHost          # Your DNS name pointing to ingress IP
    value: 'mcp.example.com'
  - name: ingressClassName     # Usually 'nginx'
    value: 'nginx'
```

> **Rule of thumb:** If you find yourself editing values in `deployment.yaml`, `service.yaml`, or any pipeline file — STOP. Add the value to `vars.yml` instead.

---

## Understanding `server.py` — The Application

This is where your actual MCP server lives. Here's the sample, explained:

```python
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

# stateless_http=True is REQUIRED when running multiple replicas (replicaCount > 1).
# MCP sessions are otherwise stored in memory on a single pod, which breaks
# when the ingress routes requests to different pods.
mcp = FastMCP("fastmcp-server", stateless_http=True)


# This is a TOOL — a function the AI model can call.
# Replace this with your real tools.
@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


# Health endpoint for Kubernetes readiness/liveness probes.
# MCP servers don't have one by default, so we add it explicitly.
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")


if __name__ == "__main__":
    # transport="http" exposes the server over the network at the /mcp/ path.
    mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp/")
```

**Three things you must keep:**

1. `stateless_http=True` — needed for the multi-replica deployment to work correctly
2. The `/health` custom route — Kubernetes probes depend on it; remove it and your pods will never become "ready"
3. `host="0.0.0.0"` — binds to all interfaces so the container is reachable; `127.0.0.1` would only work inside the pod

**What you change:** Add your own tools using the `@mcp.tool` decorator. Each tool becomes a capability the AI model can call.

---

## How the Pipeline Works

### Stage 1 — Build & Push (`pipelines/build-push.yml`)

1. Reads the `Dockerfile` from your repo root
2. Builds the image (which runs `python server.py` when started)
3. Pushes it to ACR with two tags: the build ID (e.g. `1234`) and `latest`

Result: `<acrName>.azurecr.io/<imageRepository>:<buildId>` is now available in ACR.

### Stage 2 — Deploy (`pipelines/deploy.yml`)

1. **Replace Tokens** — replaces every `{{varName}}` in `k8s/*.yaml` with values from `vars.yml`
2. **Get AKS credentials** — connects `kubectl` to your cluster
3. **Create namespace** if it doesn't exist (idempotent — safe to re-run)
4. **Apply manifests** — `kubectl apply -f k8s/`
5. **Wait for rollout** — fails the pipeline if pods don't become healthy within 5 minutes

---

## How K8s Manifests Get Their Values

K8s manifests use `{{token}}` placeholders that look like this:

```yaml
# k8s/deployment.yaml (template)
metadata:
  name: {{appName}}
spec:
  replicas: {{replicaCount}}
```

At deploy time, the **Replace Tokens** task substitutes them:

```yaml
# After token replacement
metadata:
  name: fastmcp-server
spec:
  replicas: 2
```

So you never edit raw values in the manifests — they always come from `vars.yml`.

---

## Verifying Your Deployment

After the pipeline succeeds, verify everything is working:

### 1. Connect to your AKS cluster locally

```bash
az aks get-credentials \
  --resource-group <aksResourceGroup> \
  --name <aksClusterName>
```

### 2. Check the pods are running

```bash
kubectl get pods -n <aksNamespace>
```

Expected output:
```
NAME                              READY   STATUS    RESTARTS   AGE
fastmcp-server-7d8b9c4f5-abcde    1/1     Running   0          1m
fastmcp-server-7d8b9c4f5-fghij    1/1     Running   0          1m
```

### 3. Check the service and ingress

```bash
kubectl get svc -n <aksNamespace>
kubectl get ingress -n <aksNamespace>
```

### 4. Test the health endpoint

```bash
curl https://<ingressHost>/health
```

Expected response:
```
OK
```

### 5. Confirm the MCP endpoint responds

```bash
curl -i https://<ingressHost>/mcp/
```

You should get an HTTP response from the server (not a connection error). MCP clients connect to this same `/mcp/` URL.

---

## Common Issues & Fixes

| Problem | Fix |
|---|---|
| `ImagePullBackOff` on pods | AKS doesn't have `AcrPull` permission. Run `az aks update --attach-acr` (see [Azure Setup](#one-time-azure-setup)) |
| Pods never become `READY 1/1` | The `/health` route is missing from `server.py`, or the app isn't listening on `appPort` |
| `404 Not Found` at the ingress URL | DNS not yet pointing to ingress IP, or ingress controller not installed |
| Pipeline fails at `Replace tokens` step | "Replace Tokens" extension not installed in your DevOps organisation |
| Pipeline fails at `kubectl apply` | Service connection lacks permissions on AKS cluster |
| Pods stuck in `CrashLoopBackOff` | Check `kubectl logs <pod-name> -n <namespace>` — usually app code error |
| MCP client behaves oddly with 2+ replicas | Make sure `stateless_http=True` is set in `server.py` |
| MCP client gets connection errors | Confirm the client is using the full `/mcp/` path, not just the host |

---

## Customisation Guide

### Add a real tool

Edit `server.py`:

```python
@mcp.tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    # your real logic here
    return f"Weather for {city}: sunny"
```

Every function with `@mcp.tool` becomes a capability the AI model can call.

### Add a resource (read-only data for the AI)

```python
@mcp.resource("config://version")
def get_version() -> str:
    """Expose the server version."""
    return "1.0.0"
```

### Change the number of replicas

Edit `vars.yml`:
```yaml
- name: replicaCount
  value: '3'
```

> Remember: any replica count above 1 requires `stateless_http=True` in `server.py` (already set).

### Add environment variables (e.g. API keys, DB URLs)

Edit `k8s/deployment.yaml`, add under the container spec:

```yaml
containers:
  - name: {{appName}}
    image: {{acrName}}.azurecr.io/{{imageRepository}}:{{imageTag}}
    env:
      - name: DATABASE_URL
        value: "postgresql://..."
      - name: API_KEY
        value: "your-key"
```

> For secrets, prefer a Kubernetes Secret or Azure Key Vault over plain `value:` entries.

### Change the MCP path or port

Update both `server.py` (the `mcp.run(...)` call) and `vars.yml` (`mcpPath`, `appPort`) so they stay in sync.

### Use a different domain

Edit `vars.yml`:
```yaml
- name: ingressHost
  value: 'my-mcp-server.example.com'
```

Then update your DNS to point this domain to the ingress IP.

---

## Where to Get Help

- **Pipeline logs:** Azure DevOps → Pipelines → click the failed run → expand the failing step
- **Pod logs:** `kubectl logs <pod-name> -n <namespace>`
- **Pod details:** `kubectl describe pod <pod-name> -n <namespace>`
- **Recent events:** `kubectl get events -n <namespace> --sort-by='.lastTimestamp'`
- **FastMCP docs:** https://gofastmcp.com

---

## Quick Reference — Common kubectl Commands

```bash
# Watch pods in real time
kubectl get pods -n <namespace> -w

# View logs (last 100 lines, follow)
kubectl logs -n <namespace> <pod-name> --tail=100 -f

# Restart a deployment
kubectl rollout restart deployment/<appName> -n <namespace>

# Scale manually
kubectl scale deployment/<appName> -n <namespace> --replicas=3

# Delete everything in the namespace
kubectl delete all --all -n <namespace>
```
