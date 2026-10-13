"""Convierte un mensaje de WhatsApp en ticket con tu David corriendo en Ollama.

    python3 ticket.py "buenas, ocupo media docena de tubos de media para hoy, tengo una fuga"

Usa el mismo prompt con el que se entrenó el modelo. Solo necesita Python 3 (sin paquetes extra).
"""

import json
import sys
import urllib.request

MODELO = "david-ferreteria"
PROMPT = """Eres el asistente de Ferretería La Ceiba, en Guatemala. Convierte el mensaje del cliente en un ticket JSON con estos campos:
- tipo: pedido, cotizacion, reclamo o seguimiento
- categoria: obra_gris, techos, plomeria, electricidad, pintura, herramientas o jardin
- producto: el nombre del producto como lo vende la tienda, en singular
- cantidad: número entero, o null si no la dice
- monto_q: monto en quetzales, o null si no lo dice
- urgencia: alta, media o baja
Responde solo con el JSON.

Mensaje: {mensaje}"""


def ticket(mensaje):
    cuerpo = {
        "model": MODELO,
        "stream": False,
        "think": False,
        "messages": [{"role": "user", "content": PROMPT.format(mensaje=mensaje)}],
        "options": {"temperature": 0},
    }
    pedido = urllib.request.Request("http://localhost:11434/api/chat", data=json.dumps(cuerpo).encode(),
                                    headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=120) as r:
        return json.load(r)["message"]["content"].strip()


if __name__ == "__main__":
    print(ticket(" ".join(sys.argv[1:]) or "buenas, ocupo 3 bolsas de cemento para hoy"))
