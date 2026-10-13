#!/usr/bin/env bash
# Publica solucion/ en Cloud Run como sitio estático (nginx).
#   PROYECTO=<tu-proyecto> referencia/desplegar.sh
set -euo pipefail
cd "$(dirname "$0")/.."
: "${PROYECTO:?Define PROYECTO con el ID de tu proyecto de Google Cloud}"
REGION="${REGION:-us-central1}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/referencia"
cp -R solucion "$TMP/solucion"
cp referencia/nginx.conf "$TMP/referencia/"
cp referencia/Dockerfile "$TMP/Dockerfile"
gcloud run deploy codelab-gemma-navegador \
  --source "$TMP" \
  --project "$PROYECTO" \
  --region "$REGION" \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 --memory 256Mi \
  --min-instances 0 --max-instances 2 \
  --quiet
gcloud run services describe codelab-gemma-navegador --project "$PROYECTO" --region "$REGION" \
  --format 'value(metadata.annotations."run.googleapis.com/urls")'
