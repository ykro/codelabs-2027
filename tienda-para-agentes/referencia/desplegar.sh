#!/usr/bin/env bash
# Despliega la referencia en línea en Cloud Run: la tienda de inicio (0/8) y la terminada (8/8).
#   PROYECTO=tu-proyecto ./referencia/desplegar.sh
set -euo pipefail
cd "$(dirname "$0")/.."
: "${PROYECTO:?Define PROYECTO con el ID de tu proyecto de Google Cloud}"
REGION="${REGION:-us-central1}"
TMP="$(mktemp -d)"

armar() {  # armar CARPETA_DESTINO CARPETA_TIENDA
  mkdir -p "$1"
  rsync -a --exclude .venv --exclude __pycache__ --exclude .llave_tienda.pem "$2"/ "$1"/
  cp referencia/Dockerfile "$1"/
  (cd "$1" && uv export --frozen --no-dev --no-hashes --quiet -o requirements.txt)
  printf '.venv\n__pycache__\n.llave_tienda.pem\n' > "$1"/.dockerignore
  printf '.venv/\n__pycache__/\n.llave_tienda.pem\n' > "$1"/.gcloudignore
}

desplegar() {  # desplegar SERVICIO CARPETA [variables]
  gcloud run deploy "$1" --source "$2" --project "$PROYECTO" --region "$REGION" \
    --allow-unauthenticated --max-instances 1 --min-instances 0 --memory 512Mi --cpu 1 \
    --concurrency 40 --set-env-vars "$3" --quiet
}

url_con_hash() {
  gcloud run services describe "$1" --project "$PROYECTO" --region "$REGION" --format=json \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print([u for u in json.loads(d['metadata']['annotations']['run.googleapis.com/urls']) if u.endswith('.a.run.app')][0])"
}

armar "$TMP/inicio" inicio
desplegar codelab-tienda-cafe-inicio "$TMP/inicio" "APP_MODULE=app:app"
INICIO="$(url_con_hash codelab-tienda-cafe-inicio)"

armar "$TMP/final" solucion
cp referencia/servidor.py "$TMP/final"/
cp -r referencia/plantillas_referencia "$TMP/final"/
desplegar codelab-tienda-cafe "$TMP/final" "URL_INICIO=$INICIO"
echo "Tienda de inicio:    $INICIO"
echo "Tienda terminada:    $(url_con_hash codelab-tienda-cafe)"
