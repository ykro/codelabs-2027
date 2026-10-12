# Haz que un agente use tu app

Codelab de la charla «Built for Agents: Making Your Apps Usable by AI». Construyes un servidor MCP para la agenda de Taller Volcán (un taller mecánico ficticio de Guatemala), un agente con Gemini que lo usa, y una página donde la persona aprueba las citas que el agente pide.

- `codelab.md`: el taller paso a paso (el sitio se genera desde aquí).
- `inicio/`: el código con el que empiezas, con líneas `TODO paso N` donde escribes.
- `solucion/`: el resultado exacto de seguir los pasos.
- `referencia/`: la versión en línea (`solucion/` + una página de chat), cómo desplegarla en Cloud Run y cómo tomar las capturas.
- `tests/`: pruebas de `solucion/` y una prueba que verifica que cada bloque de código del codelab aparece igual en `solucion/`.
- `assets/`: capturas de la referencia en línea.

Correr las pruebas:

```bash
cd solucion
uv run --group pruebas pytest ../tests
```

Referencia en línea: https://codelab-taller-volcan-z63pqhhmxq-uc.a.run.app

Datos ficticios: los servicios, precios y horarios de `agenda.py` son inventados; las horas ocupadas salen de un generador pseudoaleatorio con la fecha como semilla.
