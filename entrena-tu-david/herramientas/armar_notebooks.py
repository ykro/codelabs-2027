"""Arma los dos notebooks del taller a partir de una sola lista de celdas.

    python3 entrena-tu-david/herramientas/armar_notebooks.py

- solucion/entrena_tu_david.ipynb: todas las celdas completas (la referencia; se ejecuta en una T4).
- inicio/entrena_tu_david.ipynb: igual, pero las celdas marcadas con TODO quedan vacías con una indicación.

Si el notebook de solución ya tiene salidas (corrida en T4), este script no lo toca a menos que pases --forzar.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
REPO_RAW = "https://raw.githubusercontent.com/ykro/codelabs-2027/main/entrena-tu-david/datos"
COLAB = "https://colab.research.google.com/github/ykro/codelabs-2027/blob/main/entrena-tu-david/inicio/entrena_tu_david.ipynb"
CODELAB = "https://github.com/ykro/codelabs-2027/tree/main/entrena-tu-david"

# (tipo, texto, todo) — todo = indicación que ve el alumno en inicio/ en lugar del código
CELDAS: list[tuple[str, str, str | None]] = []


def md(texto: str) -> None:
    CELDAS.append(("markdown", texto.strip("\n"), None))


def code(texto: str, todo: str | None = None) -> None:
    CELDAS.append(("code", texto.strip("\n"), todo))


md(f"""
# Entrena a tu propio David

Ajusta **Gemma 4 E2B** con LoRA para que convierta mensajes de WhatsApp de una ferretería en tickets JSON.
Sigue el codelab paso a paso: cada sección de este notebook corresponde a un paso.

- Entorno: Colab con GPU **T4** (menú *Entorno de ejecución → Cambiar tipo de entorno de ejecución → T4 GPU*).
- No uses *Ejecutar todo*: corre las celdas en orden, una por una, mientras lees el paso.
- Código y datos: [{CODELAB}]({CODELAB})
""")

# ---------------------------------------------------------------- Paso 3
md("## Paso 3 · Abre el notebook e instala Unsloth")
code("""
!nvidia-smi --query-gpu=name,memory.total --format=csv
""")
code("""
%%capture
!pip install --no-deps unsloth==2026.10.4 unsloth_zoo==2026.10.4 bitsandbytes==0.50.2 trl==1.15.0 cut_cross_entropy==25.1.1
!pip install sentencepiece protobuf "datasets==4.8.5" "huggingface_hub>=1.5.0,<2.0" hf_transfer gradio==6.26.0
!pip install --no-deps transformers==5.5.0 "tokenizers>=0.22.0,<=0.23.0" "torchao>=0.16.0"
""")
code("""
import unsloth, transformers, trl, peft, gradio
print("unsloth", unsloth.__version__, "· transformers", transformers.__version__,
      "· trl", trl.__version__, "· peft", peft.__version__, "· gradio", gradio.__version__)
""")

# ---------------------------------------------------------------- Paso 4
md("## Paso 4 · Carga Gemma 4 E2B")
code("""
from unsloth import FastModel
from unsloth.chat_templates import get_chat_template

model, tokenizer = FastModel.from_pretrained(
    model_name="unsloth/gemma-4-E2B-it",
    max_seq_length=1024,
    load_in_4bit=False,
)
tokenizer = get_chat_template(tokenizer, chat_template="gemma-4")
""")
code("""
import torch

gpu = torch.cuda.get_device_properties(0)
print(f"GPU: {gpu.name} · memoria total: {gpu.total_memory / 1024**3:.1f} GB")
print(f"Memoria reservada después de cargar: {torch.cuda.max_memory_reserved() / 1024**3:.1f} GB")
""")

# ---------------------------------------------------------------- Paso 5
md("## Paso 5 · Mira el dataset y escribe el prompt")
code(f"""
import json, os, urllib.request

URL = "{REPO_RAW}"
for nombre in ["train.jsonl", "test.jsonl"]:
    if not os.path.exists(nombre):  # si subiste el archivo a Colab, usa el tuyo
        urllib.request.urlretrieve(f"{{URL}}/{{nombre}}", nombre)

train = [json.loads(linea) for linea in open("train.jsonl", encoding="utf-8")]
test = [json.loads(linea) for linea in open("test.jsonl", encoding="utf-8")]
print(f"train: {{len(train)}} ejemplos · test: {{len(test)}} ejemplos")
""")
code("""
import pandas as pd

pd.set_option("display.max_colwidth", 90)
pd.DataFrame([{"mensaje": r["mensaje"], **r["ticket"]} for r in train[:5]], dtype=object)
""")
code("""
print(json.dumps(train[0]["origen"], ensure_ascii=False, indent=1))
""")
code('''
PROMPT = """Eres el asistente de Ferretería La Ceiba, en Guatemala. Convierte el mensaje del cliente en un ticket JSON con estos campos:
- tipo: pedido, cotizacion, reclamo o seguimiento
- categoria: obra_gris, techos, plomeria, electricidad, pintura, herramientas o jardin
- producto: el nombre del producto como lo vende la tienda, en singular
- cantidad: número entero, o null si no la dice
- monto_q: monto en quetzales, o null si no lo dice
- urgencia: alta, media o baja
Responde solo con el JSON.

Mensaje: {mensaje}"""


def conversacion(mensaje, ticket=None):
    turnos = [{"role": "user", "content": [{"type": "text", "text": PROMPT.format(mensaje=mensaje)}]}]
    if ticket is not None:
        respuesta = json.dumps(ticket, ensure_ascii=False)
        turnos.append({"role": "assistant", "content": [{"type": "text", "text": respuesta}]})
    return turnos
''', todo="Escribe aquí PROMPT y la función conversacion() (paso 5 del codelab).")

# ---------------------------------------------------------------- Paso 6
md("## Paso 6 · Mide el modelo base")
code('''
import re, unicodedata

CAMPOS = ["tipo", "categoria", "producto", "cantidad", "monto_q", "urgencia"]
PERMITIDOS = {
    "tipo": ["pedido", "cotizacion", "reclamo", "seguimiento"],
    "categoria": ["obra_gris", "techos", "plomeria", "electricidad", "pintura", "herramientas", "jardin"],
    "urgencia": ["alta", "media", "baja"],
}


def normalizar(texto):
    t = unicodedata.normalize("NFKD", str(texto).lower())
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).split())


def leer_ticket(respuesta):
    """El ticket que escribió el modelo, o None si no es un JSON válido con los 6 campos."""
    texto = re.sub(r"^```(?:json)?|```$", "", respuesta.strip()).strip()
    try:
        ticket = json.loads(texto)
    except json.JSONDecodeError:
        return None
    if not isinstance(ticket, dict) or set(ticket) != set(CAMPOS):
        return None
    if any(ticket[c] not in valores for c, valores in PERMITIDOS.items()):
        return None
    return ticket


def igual(campo, a, b):
    if campo in ("cantidad", "monto_q"):
        try:
            return (a is None and b is None) or abs(float(a) - float(b)) < 0.01
        except (TypeError, ValueError):
            return False
    return normalizar(a) == normalizar(b)


def calificar(respuestas, filas):
    validos, perfectos, aciertos = 0, 0, {c: 0 for c in CAMPOS}
    for respuesta, fila in zip(respuestas, filas):
        ticket = leer_ticket(respuesta)
        if ticket is None:
            continue
        validos += 1
        bien = [igual(c, ticket[c], fila["ticket"][c]) for c in CAMPOS]
        for c, ok in zip(CAMPOS, bien):
            aciertos[c] += ok
        perfectos += all(bien)
    n = len(filas)
    return {"JSON válido": validos / n,
            "Campos correctos": sum(aciertos.values()) / (n * len(CAMPOS)),
            "Tickets perfectos": perfectos / n,
            **{f"· {c}": aciertos[c] / n for c in CAMPOS}}


def tabla(**columnas):
    return pd.DataFrame(columnas).map(lambda x: f"{x:.0%}")
''')
code('''
import time

texto_tok = getattr(tokenizer, "tokenizer", tokenizer)


def responder(mensajes, lote=16):
    texto_tok.padding_side = "left"  # para generar, el relleno va a la izquierda
    salidas = []
    for i in range(0, len(mensajes), lote):
        prompts = [tokenizer.apply_chat_template(conversacion(m), tokenize=False, add_generation_prompt=True)
                   for m in mensajes[i:i + lote]]
        entrada = texto_tok(prompts, return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
        salida = model.generate(**entrada, max_new_tokens=96, do_sample=False)
        salidas += texto_tok.batch_decode(salida[:, entrada["input_ids"].shape[1]:], skip_special_tokens=True)
    return salidas
''')
code('''
FastModel.for_inference(model)
inicio = time.time()
respuestas_base = responder([r["mensaje"] for r in test])
print(f"{len(test)} mensajes en {time.time() - inicio:.0f} s")
base = calificar(respuestas_base, test)
tabla(**{"Gemma sin ajustar": base})
''')
code('''
for fila, respuesta in list(zip(test, respuestas_base))[:3]:
    print("MENSAJE  ", fila["mensaje"])
    print("ESPERADO ", json.dumps(fila["ticket"], ensure_ascii=False))
    print("BASE     ", " ".join(respuesta.split()), "\\n")
''')

# ---------------------------------------------------------------- Paso 7
md("## Paso 7 · Configura LoRA")
code('''
model = FastModel.get_peft_model(
    model,
    finetune_vision_layers=False,     # solo texto: la parte de visión queda congelada
    finetune_language_layers=True,
    finetune_attention_modules=True,  # q, k, v, o
    finetune_mlp_modules=True,        # gate, up, down
    r=16,                             # tamaño de las matrices pequeñas que sí aprenden
    lora_alpha=16,                    # cuánto pesa lo aprendido (alpha / r = 1)
    lora_dropout=0,
    bias="none",
    random_state=3407,
)
model.print_trainable_parameters()
''', todo="Configura el adaptador LoRA con FastModel.get_peft_model (paso 7 del codelab).")

# ---------------------------------------------------------------- Paso 8
md("## Paso 8 · Entrena")
code('''
from datasets import Dataset

textos = [tokenizer.apply_chat_template(conversacion(r["mensaje"], r["ticket"]), tokenize=False).removeprefix("<bos>")
          for r in train]
datos = Dataset.from_dict({"text": textos})
print(textos[0])
''')
code('''
from trl import SFTTrainer, SFTConfig
from unsloth.chat_templates import train_on_responses_only

trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=datos,
    args=SFTConfig(
        dataset_text_field="text",
        per_device_train_batch_size=4,
        gradient_accumulation_steps=2,   # 4 x 2 = 8 ejemplos por paso
        num_train_epochs=2,              # cada ejemplo se ve 2 veces
        learning_rate=2e-4,
        warmup_steps=10,
        lr_scheduler_type="linear",
        optim="adamw_8bit",
        weight_decay=0.001,
        logging_steps=25,
        seed=3407,
        output_dir="salidas",
        report_to="none",
    ),
)
trainer = train_on_responses_only(trainer)  # solo aprende de la respuesta (el JSON), no del prompt
''', todo="Configura el entrenamiento con SFTTrainer y SFTConfig (paso 8 del codelab).")
code('''
FastModel.for_training(model)
stats = trainer.train()
print(f"Entrenamiento: {stats.metrics['train_runtime'] / 60:.1f} min")
print(f"Pico de memoria de GPU: {torch.cuda.max_memory_reserved() / 1024**3:.1f} GB de {gpu.total_memory / 1024**3:.1f} GB")
''')

# ---------------------------------------------------------------- Paso 9
md("## Paso 9 · Mide tu David")
code('''
FastModel.for_inference(model)
respuestas_david = responder([r["mensaje"] for r in test])
david = calificar(respuestas_david, test)
tabla(**{"Gemma sin ajustar": base, "Tu David": david})
''')
code('''
cambios = [(f, b, d) for f, b, d in zip(test, respuestas_base, respuestas_david)
           if leer_ticket(d) and all(igual(c, leer_ticket(d)[c], f["ticket"][c]) for c in CAMPOS)
           and not (leer_ticket(b) and all(igual(c, leer_ticket(b)[c], f["ticket"][c]) for c in CAMPOS))]
print(f"{len(cambios)} mensajes que el modelo base fallaba y tu David resuelve. Tres de ellos:\\n")
for fila, b, d in cambios[:3]:
    print("MENSAJE ", fila["mensaje"])
    print("BASE    ", " ".join(b.split()))
    print("DAVID   ", d.strip(), "\\n")
''')
code('''
model.save_pretrained("david_lora")
_ = tokenizer.save_pretrained("david_lora")
!du -sh david_lora
''')
md("### Opcional: compáralo con Gemini (Goliat)\nNecesitas tu llave de AI Studio guardada en los *Secretos* de Colab con el nombre `GEMINI_API_KEY`. Sin llave, la celda solo avisa y puedes seguir.")
code('''
# Opcional: si no tienes llave de AI Studio, esta celda solo avisa y puedes seguir al paso 10.
from google import genai
from google.colab import userdata

MODELO_GEMINI = "gemini-3.8-flash"  # si llegas al límite del día: "gemini-3.5-flash-lite"
try:
    cliente = genai.Client(api_key=userdata.get("GEMINI_API_KEY"))
except Exception:
    cliente = None
    print("No encontré GEMINI_API_KEY en los secretos de Colab (o no le diste acceso). Salta este paso.")

if cliente:
    INSTRUCCIONES = (PROMPT.split("\\n\\nMensaje:")[0] + "\\nVas a recibir varios mensajes numerados. "
                     "Responde con un arreglo JSON: un ticket por mensaje, en el mismo orden.")
    respuestas_gemini = []
    for i in range(0, len(test), 25):  # 25 mensajes por solicitud: 6 solicitudes en total
        grupo = test[i:i + 25]
        lista = "\\n".join(f"{n}. {r['mensaje']}" for n, r in enumerate(grupo, 1))
        inicio = time.time()
        r = cliente.models.generate_content(model=MODELO_GEMINI, contents=f"{INSTRUCCIONES}\\n\\nMensajes:\\n{lista}",
                                            config={"response_mime_type": "application/json", "temperature": 0})
        tickets = json.loads(r.text)[:len(grupo)]
        respuestas_gemini += [json.dumps(t, ensure_ascii=False) for t in tickets] + [""] * (len(grupo) - len(tickets))
        print(f"{len(respuestas_gemini)}/{len(test)} mensajes ({time.time() - inicio:.0f} s)")
    gemini = calificar(respuestas_gemini, test)
    display(tabla(**{"Gemma sin ajustar": base, "Tu David": david, "Gemini (Goliat)": gemini}))
''')

md("## Paso 10 · Pruébalo en una app")
code('''
import gradio as gr
from html import escape

COLORES = {"alta": "#b42318", "media": "#b54708", "baja": "#067647"}


def tarjeta(respuesta):
    ticket = leer_ticket(respuesta)
    if ticket is None:
        return f'<div class="t mal"><b>No es un ticket válido</b><pre>{escape(respuesta.strip())}</pre></div>'
    filas = "".join(f"<dt>{c}</dt><dd>{escape('—' if ticket[c] is None else str(ticket[c]))}</dd>"
                    for c in CAMPOS if c != "urgencia")
    color = COLORES[ticket["urgencia"]]
    return (f'<div class="t"><span class="u" style="background:{color}">urgencia {ticket["urgencia"]}</span>'
            f"<dl>{filas}</dl></div>")


def crear_ticket(mensaje):
    FastModel.for_inference(model)
    david = responder([mensaje])[0]
    with model.disable_adapter():
        sin_ajustar = responder([mensaje])[0]
    return tarjeta(david), tarjeta(sin_ajustar)


CSS = """
.gradio-container {max-width: 760px !important; margin: auto; font-size: 16px}
.t {border: 1px solid #d0d5dd; border-radius: 12px; padding: 14px; background: #fff}
.t.mal {border-color: #fda29b; background: #fef3f2}
.t pre {white-space: pre-wrap; font-size: 14px}
.t dl {display: grid; grid-template-columns: auto 1fr; gap: 6px 12px; margin: 10px 0 0}
.t dt {color: #475467} .t dd {margin: 0; font-weight: 600; overflow-wrap: anywhere}
.u {color: #fff; border-radius: 999px; padding: 3px 10px; font-size: 14px}
button {min-height: 48px}
"""
CLARO = "() => { document.body.classList.remove('dark'); }"
ejemplos = [f["mensaje"] for f, _, _ in cambios[:4]]

with gr.Blocks(title="Ferretería La Ceiba · tickets") as app:
    gr.Markdown("## Ferretería La Ceiba\\nPega un mensaje de WhatsApp y tu modelo lo convierte en ticket.")
    mensaje = gr.Textbox(label="Mensaje del cliente", lines=3,
                         placeholder="buenas, ocupo 3 bolsas de cemento para hoy, la obra está parada")
    boton = gr.Button("Crear ticket", variant="primary")
    with gr.Row():
        with gr.Column():
            gr.Markdown("**Tu David (ajustado)**")
            salida_david = gr.HTML()
        with gr.Column():
            gr.Markdown("**Gemma 4 E2B sin ajustar**")
            salida_base = gr.HTML()
    gr.Examples(ejemplos, inputs=mensaje, label="Ejemplos del test")
    boton.click(crear_ticket, mensaje, [salida_david, salida_base])

app.launch(share=True, css=CSS, js=CLARO, theme=gr.themes.Default(font=["Inter", "system-ui", "sans-serif"]))
''', todo="Escribe la app de Gradio (paso 10 del codelab).")

# ---------------------------------------------------------------- Paso 11
md("## Paso 11 · Llévalo a tu laptop con Ollama (opcional)\nExporta solo el adaptador a GGUF (unos 50 MB). El modelo completo no cabe en la RAM de Colab gratis al convertirlo.")
code('''
!git -c advice.detachedHead=false clone -q --depth 1 --branch b11541 https://github.com/ggml-org/llama.cpp
!pip install -q --no-deps ./llama.cpp/gguf-py
''')
code('''
!python llama.cpp/convert_lora_to_gguf.py david_lora --outfile david-lora.gguf --outtype f16 2>&1 | tail -n 2
!ls -lh david-lora.gguf
''')


def notebook(inicio: bool) -> dict:
    celdas = []
    for i, (tipo, texto, todo) in enumerate(CELDAS):
        if inicio and todo:
            texto = f"# TODO: {todo}\n"
        celda = {"cell_type": tipo, "id": f"c{i:02d}", "metadata": {}, "source": texto.splitlines(keepends=True)}
        if tipo == "code":
            celda.update(execution_count=None, outputs=[])
        celdas.append(celda)
    return {
        "nbformat": 4, "nbformat_minor": 5, "cells": celdas,
        "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
                     "kernelspec": {"name": "python3", "display_name": "Python 3"},
                     "language_info": {"name": "python"}},
    }


def main() -> None:
    forzar = "--forzar" in sys.argv
    destino_sol = AQUI / "solucion" / "entrena_tu_david.ipynb"
    ya_corrido = destino_sol.exists() and any(
        c.get("outputs") for c in json.loads(destino_sol.read_text(encoding="utf-8"))["cells"] if c["cell_type"] == "code")
    salidas = [(AQUI / "inicio" / "entrena_tu_david.ipynb", notebook(True))]
    if forzar or not ya_corrido:
        salidas.append((destino_sol, notebook(False)))
    for ruta, nb in salidas:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("escrito", ruta.relative_to(AQUI))


if __name__ == "__main__":
    main()
