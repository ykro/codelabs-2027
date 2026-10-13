# Entrena a tu propio David

Taller de la charla «David vs. Goliath»: ajustas Gemma 4 E2B con LoRA (Unsloth) en Colab gratis para que convierta mensajes de WhatsApp de una ferretería ficticia de Guatemala en tickets JSON, lo mides contra el modelo sin ajustar, lo pruebas en una app de Gradio y lo exportas a GGUF para Ollama.

El texto del taller está en [`codelab.md`](codelab.md) (publicado en el sitio de los codelabs).

| Carpeta o archivo | Qué tiene |
|---|---|
| `inicio/entrena_tu_david.ipynb` | el notebook que abres en Colab; tiene 4 celdas `TODO` que completas siguiendo el taller |
| `solucion/entrena_tu_david.ipynb` | el notebook completo, con las salidas de una corrida de principio a fin (se ve en GitHub) |
| `solucion/Modelfile`, `ticket.py` | lo que usas en tu laptop con Ollama (paso 11); `ticket.py` también está en `inicio/` |
| `datos/` | el dataset (`train.jsonl`, `test.jsonl`, CC BY 4.0), cómo se generó y validó ([`DATOS.md`](datos/DATOS.md)) y el script que lo generó |
| `assets/` | capturas que usa el taller |
| `herramientas/armar_notebooks.py` | arma los dos notebooks desde una sola lista de celdas |
| `tests/` | pruebas del dataset, de las funciones de calificación y de que el código del taller sea el mismo que el del notebook |

Abrir el notebook en Colab:
[colab.research.google.com/github/ykro/codelabs-2027/blob/main/entrena-tu-david/inicio/entrena_tu_david.ipynb](https://colab.research.google.com/github/ykro/codelabs-2027/blob/main/entrena-tu-david/inicio/entrena_tu_david.ipynb)

Pruebas (desde la raíz del repo):

```bash
uv run --with pytest --with pandas pytest entrena-tu-david/tests -q
```
