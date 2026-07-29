#!/usr/bin/env bash
#
# One-time GCP infrastructure bootstrap for pae-rtac-server.
#
# This provisions the infra the k8s manifests + CI/CD assume already exists:
# Artifact Registry, a GKE Autopilot cluster, Cloud SQL (Postgres), Memorystore
# (Redis), Secret Manager entries, and Workload Identity Federation for both the
# in-cluster Cloud SQL proxy and the GitHub Actions deployer.
#
# It is idempotent-ish (uses `|| true` on create calls) but review each step —
# this is a documented, reviewable alternative to Terraform, NOT a hands-off
# installer. Run the blocks you need. Requires: gcloud, an authenticated user
# with project-admin rights. See docs/DEPLOYMENT.md for the full walkthrough.
#
set -euo pipefail

# --------------------------------------------------------------------------
# Fill these in before running.
# --------------------------------------------------------------------------
PROJECT_ID="${PROJECT_ID:?set PROJECT_ID}"
REGION="${REGION:-us-central1}"
GITHUB_REPO="${GITHUB_REPO:?set GITHUB_REPO, e.g. your-org/rtac_modbus_server}"

AR_REPO="pae"
CLUSTER="pae-autopilot"
SQL_INSTANCE="rtac-pg-prod"       # matches k8s/overlays/prod INSTANCE_CONNECTION_NAME
SQL_DB="rtac_modbus"
SQL_USER="rtac_user"
REDIS_INSTANCE="rtac-redis-prod"
K8S_NAMESPACE="rtac-modbus-prod"
KSA="pae-rtac-server"             # matches ServiceAccount in k8s/base
DEPLOYER_GSA="gh-deployer"        # GitHub Actions deploy identity
SQLPROXY_GSA="rtac-modbus-prod"   # matches overlay SA annotation

gcloud config set project "$PROJECT_ID"

# --------------------------------------------------------------------------
# 1. Enable APIs
# --------------------------------------------------------------------------
gcloud services enable \
  container.googleapis.com \
  artifactregistry.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  redis.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com

# --------------------------------------------------------------------------
# 2. Artifact Registry (Docker)
# --------------------------------------------------------------------------
gcloud artifacts repositories create "$AR_REPO" \
  --repository-format=docker --location="$REGION" \
  --description="PAE microservice images" || true

# --------------------------------------------------------------------------
# 3. GKE Autopilot cluster (Workload Identity is on by default in Autopilot)
# --------------------------------------------------------------------------
gcloud container clusters create-auto "$CLUSTER" --region="$REGION" || true

# --------------------------------------------------------------------------
# 4. Cloud SQL (PostgreSQL 16) — plain Postgres is sufficient (no TimescaleDB)
# --------------------------------------------------------------------------
gcloud sql instances create "$SQL_INSTANCE" \
  --database-version=POSTGRES_16 --region="$REGION" \
  --edition=ENTERPRISE --tier=db-custom-1-3840 --storage-auto-increase || true
gcloud sql databases create "$SQL_DB" --instance="$SQL_INSTANCE" || true

PG_PASSWORD="$(openssl rand -base64 24)"
gcloud sql users create "$SQL_USER" --instance="$SQL_INSTANCE" --password="$PG_PASSWORD" || \
  gcloud sql users set-password "$SQL_USER" --instance="$SQL_INSTANCE" --password="$PG_PASSWORD"

SQL_CONN_NAME="$(gcloud sql instances describe "$SQL_INSTANCE" --format='value(connectionName)')"
echo "INSTANCE_CONNECTION_NAME = ${SQL_CONN_NAME}   (put this in k8s/overlays/prod)"

# --------------------------------------------------------------------------
# 5. Memorystore (Redis)
# --------------------------------------------------------------------------
gcloud redis instances create "$REDIS_INSTANCE" \
  --size=1 --region="$REGION" --redis-version=redis_7_0 || true
REDIS_IP="$(gcloud redis instances describe "$REDIS_INSTANCE" --region="$REGION" --format='value(host)')"
echo "REDIS_HOST = ${REDIS_IP}   (put this in k8s/overlays/prod configMapGenerator)"

# --------------------------------------------------------------------------
# 6. Secret Manager — store the DB password
# --------------------------------------------------------------------------
printf '%s' "$PG_PASSWORD" | gcloud secrets create rtac-postgres-password --data-file=- || \
printf '%s' "$PG_PASSWORD" | gcloud secrets versions add rtac-postgres-password --data-file=-

# --------------------------------------------------------------------------
# 7. Cloud SQL proxy identity (Workload Identity: KSA -> GSA)
# --------------------------------------------------------------------------
gcloud iam service-accounts create "$SQLPROXY_GSA" \
  --display-name="rtac-modbus prod Cloud SQL client" || true
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SQLPROXY_GSA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
# Allow the k8s ServiceAccount to impersonate the GSA.
gcloud iam service-accounts add-iam-policy-binding \
  "${SQLPROXY_GSA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:${PROJECT_ID}.svc.id.goog[${K8S_NAMESPACE}/${KSA}]"

# --------------------------------------------------------------------------
# 8. GitHub Actions deployer via Workload Identity Federation (keyless)
# --------------------------------------------------------------------------
gcloud iam service-accounts create "$DEPLOYER_GSA" \
  --display-name="GitHub Actions deployer" || true
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_GSA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud iam workload-identity-pools create github --location=global \
  --display-name="GitHub Actions" || true
gcloud iam workload-identity-pools providers create-oidc github \
  --location=global --workload-identity-pool=github \
  --display-name="GitHub OIDC" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${GITHUB_REPO}'" \
  --issuer-uri="https://token.actions.githubusercontent.com" || true

POOL_ID="$(gcloud iam workload-identity-pools describe github --location=global --format='value(name)')"
gcloud iam service-accounts add-iam-policy-binding \
  "${DEPLOYER_GSA}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_ID}/attribute.repository/${GITHUB_REPO}"

PROVIDER="$(gcloud iam workload-identity-pools providers describe github \
  --location=global --workload-identity-pool=github --format='value(name)')"

cat <<EOF

============================================================================
Done. Set these on the GitHub repo (Settings -> Secrets and variables -> Actions):

  Variables:
    GCP_PROJECT_ID = ${PROJECT_ID}
    GCP_REGION     = ${REGION}
    AR_HOST        = ${REGION}-docker.pkg.dev
    AR_REPO        = ${AR_REPO}

  Secrets:
    GCP_WORKLOAD_IDENTITY_PROVIDER = ${PROVIDER}
    GCP_DEPLOY_SERVICE_ACCOUNT     = ${DEPLOYER_GSA}@${PROJECT_ID}.iam.gserviceaccount.com

Then edit k8s/overlays/prod/kustomization.yaml placeholders:
    INSTANCE_CONNECTION_NAME -> ${SQL_CONN_NAME}
    REDIS_HOST               -> ${REDIS_IP}
    image newName            -> ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/pae-rtac-server
    SA annotation project    -> ${PROJECT_ID}
============================================================================
EOF
