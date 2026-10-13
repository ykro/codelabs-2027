# Codelabs 2027

Cuatro talleres prácticos de alrededor de una hora. Cada uno enseña una tecnología y termina con algo que funciona. Solo necesitas un navegador y una cuenta de Google.

**Sitio de los talleres:** https://codelabs-2027-z63pqhhmxq-uc.a.run.app

| Taller | Qué aprendes | Dónde corre | Referencia en línea |
|---|---|---|---|
| [Entrena a tu propio David](entrena-tu-david/) | Dataset propio, fine-tuning LoRA de Gemma 4 E2B, evaluación base vs. ajustado, exportar a GGUF | Colab gratis (GPU T4) | Notebook con salidas y capturas |
| [Haz que un agente use tu app](agente-mcp/) | Servidor MCP en Python, anotaciones de herramientas, agente propio con Gemini, aprobación humana fuera del agente | Cloud Shell | [Taller Volcán](https://codelab-taller-volcan-z63pqhhmxq-uc.a.run.app) |
| [Haz tu tienda legible para agentes](tienda-para-agentes/) | JSON-LD de schema.org, feed de productos, perfil y checkout UCP, firmas AP2 | Cloud Shell | [Tostaduría Barrilete](https://codelab-tienda-cafe-z63pqhhmxq-uc.a.run.app) |
| [Split-brain en el navegador](gemma-en-el-navegador/) | Gemma 4 E2B en el navegador con LiteRT-LM Web, detector de datos personales en código, Gemini solo con texto limpio | Chrome con WebGPU | [Pregunta sin regalar tus datos](https://codelab-gemma-navegador-z63pqhhmxq-uc.a.run.app) |

Cada taller acompaña una charla: «David vs. Goliath», «Built for Agents», «Your Next Customer Is an AI Agent» y «Engineering with Gemma». No hace falta haber visto la charla.

## Cómo está organizado cada taller

- `codelab.md`: el texto del taller. El sitio se genera a partir de él.
- `inicio/`: el código que descargas, con `TODO` donde escribes.
- `solucion/`: el resultado de seguir todos los pasos.
- `tests/`: pruebas de la solución y una prueba que verifica que el código del texto es el mismo de `solucion/`.
- `referencia/`: cómo se publica la versión en línea.

Cada paso se probó siguiéndolo tal como está escrito, en el entorno que indica el taller. Las salidas del texto salen de esas corridas.

## Generar el sitio

```bash
uv run sitio/build.py --check     # escribe sitio/dist/
npm install && npm run revisar-sitio   # revisa teléfono y laptop
scripts/revisar_fugas.sh           # sin datos que no deben publicarse
```

## Licencia

Código bajo [Apache 2.0](LICENSE). Los datos sintéticos de `entrena-tu-david/datos/` están bajo CC BY 4.0 (ver su `DATOS.md`).
