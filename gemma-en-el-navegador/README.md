# Split-brain en el navegador

Taller de la charla «Engineering with Gemma: Casos de uso y arquitecturas». Gemma 4 E2B corre en Chrome con LiteRT-LM Web (WebGPU), cambia los datos personales de un texto por marcadores, un detector escrito en JavaScript bloquea el envío si algo se escapó, Gemini responde sobre el texto limpio y la página restaura los datos en el dispositivo.

El texto del taller está en [`codelab.md`](codelab.md).

## Carpetas

| Carpeta | Qué tiene |
|---|---|
| `inicio/` | Lo que descarga el alumno: la interfaz completa y cinco archivos con `TODO` (`js/modelo.js`, `js/anonimizador.js`, `js/detector.js`, `js/gemini.js`, `js/restaurar.js`). |
| `solucion/` | El resultado de seguir todos los pasos. |
| `assets/` | Capturas de la app usadas en el taller. |
| `tests/` | Pruebas de `solucion/`, de que `inicio/` solo difiere en los cinco archivos del alumno y de que cada bloque de código del taller es idéntico a `solucion/`. |
| `referencia/` | `Dockerfile`, `nginx.conf` y `desplegar.sh` para publicar `solucion/` en Cloud Run como sitio estático. |

## Probar

```bash
cd solucion
python3 servir.py          # abre http://localhost:8000 en Chrome con WebGPU
node --test                # pruebas del detector, el mapa, Gemini (con fetch falso) y la restauración
cd ..
node --test "tests/*.test.mjs"   # lo anterior y la concordancia del taller con solucion/
```

## Notas

- No hay llaves en el código. La llave de AI Studio la escribe cada persona en la página y queda solo en su navegador.
- El modelo (`gemma-4-E2B-it-web.litertlm`, Apache 2.0) se descarga de Hugging Face la primera vez y se guarda en el almacenamiento privado del navegador (OPFS).
- Los textos de ejemplo usan datos inventados (los DPI tienen dígito verificador válido, pero no corresponden a nadie).
