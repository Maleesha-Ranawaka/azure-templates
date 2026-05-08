# FastAPI on AKS — Deployment Template

A ready-to-use Azure DevOps template for deploying a **FastAPI** application to **Azure Kubernetes Service (AKS)** using **Azure Container Registry (ACR)**.

> **Audience:** DevOps engineers new to AKS pipelines. No prior experience with this template required.

---

## Table of Contents

1. [What This Template Does](#what-this-template-does)
2. [Folder Structure](#folder-structure)
3. [Prerequisites](#prerequisites)
4. [One-Time Azure Setup](#one-time-azure-setup)
5. [One-Time Azure DevOps Setup](#one-time-azure-devops-setup)
6. [How to Use This Template](#how-to-use-this-template)
7. [Understanding `vars.yml` — The Single Point of Change](#understanding-varsyml--the-single-point-of-change)
8. [How the Pipeline Works](#how-the-pipeline-works)
9. [How K8s Manifests Get Their Values](#how-k8s-manifests-get-their-values)
10. [Verifying Your Deployment](#verifying-your-deployment)
11. [Common Issues & Fixes](#common-issues--fixes)
12. [Customisation Guide](#customisation-guide)

---

## What This Template Does

When you push code to the `main` branch, the pipeline automatically:

1. **Builds** a Docker image from your FastAPI code
2. **Pushes** that image to your Azure Container Registry (ACR)
3. **Deploys** it to your AKS cluster as a Kubernetes Deployment, exposed via Service + Ingress

The whole flow takes about 3–5 minutes.

---

## Folder Structure

```
aks-fastapi-template/
├── vars.yml                     ← SINGLE POINT OF CHANGE (edit this only)
├── azure-pipelines.yml          ← Main pipeline (2 stages: build+push, deploy)
├── Dockerfile                   ← Defines the container image
├── main.py                      ← Sample FastAPI app
├── requirements.txt             ← Python dependencies
├── pipelines/
│   ├── build-push.yml           ← Stage 1: Build + Push to ACR
│   └── deploy.yml               ← Stage 2: Deploy to AKS
└── k8s/
    ├── deployment.yaml          ← K8s Deployment (the actual pods)
    ├── service.yaml             ← K8s Service (internal load balancer)
    └── ingress.yaml             ← K8s Ingress (external access)
```

---

## Prerequisites

You need to have these things ready before using this template:

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

Copy the `EXTERNAL-IP` and create a DNS A-record pointing your domain (e.g. `fastapi.example.com`) to it.

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

### For a brand new app

1. **Copy this folder** into your application repo (or fork it)
2. **Replace `main.py` and `requirements.txt`** with your actual FastAPI code
3. **Edit `vars.yml`** — change the values to match your environment (see next section)
4. **Commit and push to `main`** — pipeline runs automatically

### For an existing app

Just drop in:
- `Dockerfile`
- `vars.yml`
- `azure-pipelines.yml`
- `pipelines/` folder
- `k8s/` folder

Then edit `vars.yml` and push.

---

## Understanding `vars.yml` — The Single Point of Change

This is the **only file you should normally edit**. Every other file reads from these values.

```yaml
variables:

  # ── Application ──
  - name: appName              # Used as K8s deployment/service/ingress name
    value: 'fastapi-app'
  - name: appPort              # Port FastAPI listens on inside the container
    value: '8000'
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
    value: 'fastapi-prod'

  # ── Container Registry (ACR) ──
  - name: acrName              # Just the name, NOT the full URL
    value: 'acrmyappprod'
  - name: acrServiceConnection # Azure DevOps service connection for ACR
    value: 'sc-acr-prod'
  - name: imageRepository      # Image name (becomes acrname.azurecr.io/imageRepository)
    value: 'fastapi-app'
  - name: imageTag             # Build ID = unique per pipeline run
    value: '$(Build.BuildId)'

  # ── Ingress ──
  - name: ingressHost          # Your DNS name pointing to ingress IP
    value: 'fastapi.example.com'
  - name: ingressClassName     # Usually 'nginx'
    value: 'nginx'
```

> **Rule of thumb:** If you find yourself editing values in `deployment.yaml`, `service.yaml`, or any pipeline file — STOP. Add the value to `vars.yml` instead.

---

## How the Pipeline Works

### Stage 1 — Build & Push (`pipelines/build-push.yml`)

1. Reads the `Dockerfile` from your repo root
2. Builds the image
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
  name: fastapi-app
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
NAME                          READY   STATUS    RESTARTS   AGE
fastapi-app-7d8b9c4f5-abcde   1/1     Running   0          1m
fastapi-app-7d8b9c4f5-fghij   1/1     Running   0          1m
```

### 3. Check the service

```bash
kubectl get svc -n <aksNamespace>
```

### 4. Check the ingress

```bash
kubectl get ingress -n <aksNamespace>
```

### 5. Hit your endpoint

```bash
curl https://<ingressHost>/health
```

Expected response:
```json
{"status": "healthy"}
```

---

## Common Issues & Fixes

| Problem | Fix |
|---|---|
| `ImagePullBackOff` on pods | AKS doesn't have `AcrPull` permission. Run `az aks update --attach-acr` (see [Azure Setup](#one-time-azure-setup)) |
| `404 Not Found` when hitting ingress URL | DNS not yet pointing to ingress IP, or ingress controller not installed |
| Pipeline fails at `Replace tokens` step | "Replace Tokens" extension not installed in your DevOps organisation |
| Pipeline fails at `kubectl apply` | Service connection lacks permissions on AKS cluster |
| Pods stuck in `CrashLoopBackOff` | Check `kubectl logs <pod-name> -n <namespace>` — usually app code error |
| `readinessProbe` failing | Your app must respond to `GET /health` with HTTP 200 |
| Image pushed but not deployed | Check Stage 2 logs in pipeline; namespace mismatch is a common cause |

---

## Customisation Guide

### Change the number of replicas

Edit `vars.yml`:
```yaml
- name: replicaCount
  value: '5'
```

### Add environment variables to your app

Edit `k8s/deployment.yaml`, add under the container spec:

```yaml
containers:
  - name: {{appName}}
    image: {{acrName}}.azurecr.io/{{imageRepository}}:{{imageTag}}
    env:
      - name: DATABASE_URL
        value: "postgresql://..."
      - name: LOG_LEVEL
        value: "INFO"
```

### Use a different domain

Edit `vars.yml`:
```yaml
- name: ingressHost
  value: 'my-new-domain.example.com'
```

Then update your DNS to point this domain to the ingress IP.

### Deploy to multiple environments (dev/staging/prod)

Create separate vars files:
- `vars.dev.yml`
- `vars.staging.yml`
- `vars.prod.yml`

Then run separate pipelines pointing to each, or use [stage parameters](https://learn.microsoft.com/en-us/azure/devops/pipelines/process/templates) to pick the right vars file per stage.

### Add health check endpoints to your FastAPI app

The K8s manifests expect `/health` to return HTTP 200. The provided `main.py` already includes this:

```python
@app.get("/health")
def health():
    return {"status": "healthy"}
```

If you remove this, your pods will fail their readiness probe and the deployment will hang.

---

## Where to Get Help

- **Pipeline logs:** Azure DevOps → Pipelines → click the failed run → expand the failing step
- **Pod logs:** `kubectl logs <pod-name> -n <namespace>`
- **Pod details:** `kubectl describe pod <pod-name> -n <namespace>`
- **Recent events:** `kubectl get events -n <namespace> --sort-by='.lastTimestamp'`

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
kubectl scale deployment/<appName> -n <namespace> --replicas=5

# Delete everything in the namespace
kubectl delete all --all -n <namespace>
```
