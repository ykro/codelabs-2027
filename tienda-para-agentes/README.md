# Haz tu tienda legible para agentes

Codelab de la charla «Your Next Customer Is an AI Agent». Llevas una tienda de café ficticia (Tostaduría Barrilete) de 0/8 a 8/8 en la auditoría de preparación para agentes: JSON-LD de schema.org, feed de productos, perfil UCP en `/.well-known/ucp`, sesión de checkout UCP y firmas AP2. Al final, un agente de compras con Gemini le compra y tú apruebas en una página de la tienda.

Las instrucciones están en [`codelab.md`](codelab.md). Sigue la especificación de UCP versión `2026-08-25`.

| Carpeta | Qué tiene |
| --- | --- |
| `inicio/` | Lo que descarga el alumno: la tienda para personas, con marcas `TODO paso N (id)` donde escribe. |
| `solucion/` | El resultado exacto de seguir el codelab. |
| `tests/` | Pruebas de `solucion/`, del auditor (0/8 en `inicio/`, 8/8 en `solucion/`) y de concordancia: aplicar los bloques del codelab sobre `inicio/` da exactamente `solucion/`. |
| `referencia/` | La referencia en línea en Cloud Run: la tienda terminada más una página de auditoría pública con límite por visitante. |
| `assets/` | Capturas que usa el codelab. |

Correr las pruebas:

```bash
cd tienda-para-agentes/solucion
uv run pytest ../tests -q
```

Desplegar la referencia (servicios `codelab-tienda-cafe` y `codelab-tienda-cafe-inicio`):

```bash
PROYECTO=tu-proyecto ./tienda-para-agentes/referencia/desplegar.sh
```

Las fotos de producto se generaron con `gemini-3.1-flash-lite-image`; los prompts están en `solucion/static/img/origen.json`. El auditor es una adaptación del de Encargo (`agent/encargo/audit.py`), con los mismos 8 puntos.
