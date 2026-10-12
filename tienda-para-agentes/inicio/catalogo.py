"""Catálogo de la Tostaduría Barrilete (tienda ficticia) y reglas de envío.

Los productos, precios y fincas son inventados para el taller. Los precios se
guardan en centavos de quetzal (7800 = Q78.00), igual que los montos de UCP.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

TIENDA = {
    "nombre": "Tostaduría Barrilete",
    "lema": "Café de altura de Guatemala, tostado cada semana en Ciudad de Guatemala.",
    "moneda": "GTQ",
}

MOLIENDAS = {
    "grano": "en grano",
    "medio": "molido medio (goteo)",
    "grueso": "molido grueso (prensa francesa)",
}


def _variantes(prefijo: str, precio_250: int, precio_454: int, agotadas: set[str]) -> list[dict]:
    combinaciones = [("250", "grano", precio_250), ("250", "medio", precio_250),
                     ("250", "grueso", precio_250), ("454", "grano", precio_454)]
    variantes = []
    for gramos, molienda, precio in combinaciones:
        sku = f"{prefijo}-{gramos}-{molienda}"
        variantes.append({
            "sku": sku,
            "gramos": int(gramos),
            "molienda": molienda,
            "presentacion": f"{gramos} g, {MOLIENDAS[molienda]}",
            "precio": precio,
            "disponible": sku not in agotadas,
        })
    return variantes


PRODUCTOS = [
    {
        "slug": "huehuetenango-altura",
        "nombre": "Huehuetenango Altura",
        "region": "Huehuetenango",
        "altura": "1,700 m",
        "proceso": "Lavado",
        "tueste": "Medio",
        "notas": "Chocolate amargo, frutos rojos y acidez brillante.",
        "variantes": _variantes("hue", 7800, 13800, {"hue-454-grano"}),
    },
    {
        "slug": "antigua-volcan",
        "nombre": "Antigua Volcán",
        "region": "Antigua Guatemala",
        "altura": "1,550 m",
        "proceso": "Lavado",
        "tueste": "Medio oscuro",
        "notas": "Cacao, especias dulces y cuerpo redondo.",
        "variantes": _variantes("ant", 7200, 12800, set()),
    },
    {
        "slug": "acatenango-miel",
        "nombre": "Acatenango Miel",
        "region": "Acatenango",
        "altura": "1,600 m",
        "proceso": "Honey",
        "tueste": "Medio claro",
        "notas": "Panela, durazno y final largo.",
        "variantes": _variantes("aca", 8500, 15000, {"aca-250-grueso"}),
    },
    {
        "slug": "coban-nublado",
        "nombre": "Cobán Nublado",
        "region": "Alta Verapaz",
        "altura": "1,400 m",
        "proceso": "Lavado",
        "tueste": "Medio",
        "notas": "Caramelo, nuez y acidez suave.",
        "variantes": _variantes("cob", 6800, 12000, {"cob-250-medio"}),
    },
]

# Envíos a domicilio en Guatemala. Montos en centavos.
ENVIOS = {
    "estandar": {
        "titulo": "Envío estándar",
        "precio": 2000,
        "preparacion": (0, 1),   # días hábiles para preparar el paquete
        "transito": (2, 2),      # días hábiles en camino
        "dias": "lunes a viernes",
    },
    "expres": {
        "titulo": "Exprés en moto",
        "precio": 3500,
        "dias": "lunes a sábado",
    },
}

ZONA_GT = timezone(timedelta(hours=-6))  # Guatemala no usa horario de verano


def hoy_gt() -> date:
    return datetime.now(ZONA_GT).date()


def producto(slug: str) -> dict | None:
    return next((p for p in PRODUCTOS if p["slug"] == slug), None)


def variante(sku: str) -> tuple[dict, dict] | tuple[None, None]:
    for p in PRODUCTOS:
        for v in p["variantes"]:
            if v["sku"] == sku:
                return p, v
    return None, None


def titulo_variante(p: dict, v: dict) -> str:
    return f"{p['nombre']} · {v['presentacion']}"


def quetzales(centavos: int) -> str:
    return f"Q{centavos / 100:,.2f}"


def sumar_dias(desde: date, dias: int, incluye_sabado: bool = False) -> date:
    """Suma días de entrega: hábiles (lunes a viernes) o de lunes a sábado."""
    actual = desde
    while dias > 0:
        actual += timedelta(days=1)
        limite = 6 if incluye_sabado else 5  # weekday(): lunes=0 … domingo=6
        if actual.weekday() < limite:
            dias -= 1
    return actual


def ventana_entrega(opcion: str, hoy: date | None = None) -> tuple[date, date]:
    hoy = hoy or hoy_gt()
    if opcion == "expres":
        dia = sumar_dias(hoy, 1, incluye_sabado=True)
        return dia, dia
    envio = ENVIOS["estandar"]
    minimo = envio["preparacion"][0] + envio["transito"][0]
    maximo = envio["preparacion"][1] + envio["transito"][1]
    return sumar_dias(hoy, minimo), sumar_dias(hoy, maximo)


DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_larga(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def rango_fechas(desde: date, hasta: date) -> str:
    if desde == hasta:
        return f"el {fecha_larga(desde)}"
    if desde.month == hasta.month:
        return f"entre el {DIAS[desde.weekday()]} {desde.day} y el {fecha_larga(hasta)}"
    return f"entre el {fecha_larga(desde)} y el {fecha_larga(hasta)}"


def momento(d: date, hora: int) -> str:
    """Fecha y hora RFC 3339 en la zona de Guatemala."""
    return datetime.combine(d, time(hora), ZONA_GT).isoformat()
