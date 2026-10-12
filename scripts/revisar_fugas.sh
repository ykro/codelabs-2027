#!/usr/bin/env bash
# Busca datos que no deben publicarse: IDs y números de proyecto, correos, llaves,
# rutas locales y URLs de Cloud Run con número de proyecto.
#   scripts/revisar_fugas.sh [ruta ...]        (por omisión, todo el repo y su historial)
#   scripts/revisar_fugas.sh https://...       (además revisa un sitio publicado)
set -uo pipefail
cd "$(dirname "$0")/.."

PATRON='611681112050|768634351594|ai-experiments|pm-innovationlab|viaticos-spending|@gmail\.com|@galileo\.edu|AIza[0-9A-Za-z_-]{30,}|ya29\.[0-9A-Za-z_-]+|sk-[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|/Users/[a-z]+|/home/[a-z]+/|hf_[A-Za-z0-9]{30,}|ghp_[A-Za-z0-9]{30,}|[a-z0-9-]+-[0-9]{9,}\.[a-z0-9-]+\.run\.app'
EXCLUIR=(--exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv --exclude-dir=dist --exclude-dir=__pycache__ --exclude-dir=.pytest_cache --exclude=*.pyc --exclude=revisar_fugas.sh --exclude=*.png --exclude=*.jpg --exclude=*.gguf --exclude=*.safetensors --exclude=package-lock.json --exclude=uv.lock)

fallas=0
locales=()
for a in "$@"; do [[ "$a" == http* ]] || locales+=("$a"); done
[[ ${#locales[@]} -eq 0 ]] && locales=(.)

if grep -rEn "${EXCLUIR[@]}" "$PATRON" "${locales[@]}"; then
  echo "✗ Hay datos que no deben publicarse en los archivos (arriba)."; fallas=1
fi
if [[ -d sitio/dist ]] && grep -rEn "$PATRON" sitio/dist --exclude=*.png; then
  echo "✗ Hay datos que no deben publicarse en sitio/dist."; fallas=1
fi
if git rev-parse --git-dir >/dev/null 2>&1 && git log --all -p -- . ':!*.lock' ':!*.png' ':!scripts/revisar_fugas.sh' 2>/dev/null | grep -En "$PATRON" | grep -v 'revisar_fugas.sh' | head -20 | grep .; then
  echo "✗ El historial de git contiene datos que no deben publicarse."; fallas=1
fi
if git rev-parse --git-dir >/dev/null 2>&1 && git log --all --format='%ae %ce' | grep -Ev 'users\.noreply\.github\.com' | grep -q @; then
  echo "✗ Hay commits con un correo personal como autor (usa el correo noreply de GitHub)."; fallas=1
fi
for url in "$@"; do
  [[ "$url" == http* ]] || continue
  if curl -fsSL "$url" | grep -En "$PATRON"; then echo "✗ $url expone datos."; fallas=1; fi
done
# Metadatos de imágenes (EXIF/GPS/autor)
if command -v exiftool >/dev/null; then
  if find . -path ./node_modules -prune -o \( -name '*.png' -o -name '*.jpg' \) -print0 | xargs -0 exiftool -q -q -GPSPosition -Author -Artist -Creator 2>/dev/null | grep .; then
    echo "✗ Hay imágenes con metadatos personales."; fallas=1
  fi
fi
[[ $fallas -eq 0 ]] && echo "✓ Sin datos expuestos."
exit $fallas
