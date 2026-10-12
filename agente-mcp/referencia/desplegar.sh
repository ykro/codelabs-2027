#!/usr/bin/env bash
# Despliega la referencia en Cloud Run: el código de solucion/ + la página de chat.
#   PROYECTO=<tu-proyecto> referencia/desplegar.sh
set -euo pipefail
: "${PROYECTO:?Define PROYECTO con el id de tu proyecto de Google Cloud}"
REGION="${REGION:-us-central1}"
SERVICIO="${SERVICIO:-codelab-taller-volcan}"
AQUI="$(cd "$(dirname "$0")" && pwd)"
CUENTA="${SERVICIO}@${PROYECTO}.iam.gserviceaccount.com"
DIR="$(mktemp -d)"
cp "$AQUI"/../solucion/{agenda,agente,paginas,servidor}.py "$AQUI"/../solucion/pyproject.toml "$AQUI"/../solucion/uv.lock "$DIR"/
cp "$AQUI"/{app.py,chat.html,Dockerfile} "$DIR"/
if ! gcloud iam service-accounts describe "$CUENTA" --project "$PROYECTO" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SERVICIO" --project "$PROYECTO" --display-name "Codelab Taller Volcán"
  gcloud projects add-iam-policy-binding "$PROYECTO" --member "serviceAccount:$CUENTA" --role roles/aiplatform.user --condition None >/dev/null
fi
# La URL con hash (…-uc.a.run.app) no contiene el número de proyecto: es la que se publica.
URL="$(gcloud run services describe "$SERVICIO" --project "$PROYECTO" --region "$REGION" --format json 2>/dev/null \
  | python3 -c 'import json,sys; u=json.loads(json.load(sys.stdin)["metadata"]["annotations"]["run.googleapis.com/urls"]); print(next(x for x in u if x.endswith(".a.run.app")))' 2>/dev/null || true)"
gcloud run deploy "$SERVICIO" --project "$PROYECTO" --region "$REGION" --source "$DIR" \
  --service-account "$CUENTA" --allow-unauthenticated --max-instances 1 --min-instances 0 \
  --memory 512Mi --cpu 1 --concurrency 20 --timeout 120 \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=$PROYECTO,GOOGLE_CLOUD_LOCATION=global,GEMINI_MODEL=gemini-3.8-flash,URL_PUBLICA=${URL_PUBLICA:-$URL}"
rm -rf "$DIR"
