"""JSON-LD de schema.org para cada página de producto."""

from __future__ import annotations

from typing import Any

from catalogo import ENVIOS, TIENDA, titulo_variante


def jsonld_producto(p: dict, base: str) -> dict[str, Any]:
    url = f"{base}/cafe/{p['slug']}"
    return {
        "@context": "https://schema.org",
        "@type": "ProductGroup",
        "@id": url,
        "name": p["nombre"],
        "description": f"Café de {p['region']}, {p['altura']}, proceso {p['proceso'].lower()}. {p['notas']}",
        "url": url,
        "image": f"{base}/static/img/{p['slug']}.jpg",
        "brand": {"@type": "Brand", "name": TIENDA["nombre"]},
        "productGroupID": p["slug"],
        "variesBy": ["https://schema.org/size"],
        "hasVariant": [
            {
                "@type": "Product",
                "@id": f"{url}#{v['sku']}",
                "sku": v["sku"],
                "name": titulo_variante(p, v),
                "size": v["presentacion"],
                "weight": {"@type": "QuantitativeValue", "value": v["gramos"], "unitCode": "GRM"},
                "offers": oferta(v, url),
            }
            for v in p["variantes"]
        ],
    }


def oferta(v: dict, url: str) -> dict[str, Any]:
    return {
        "@type": "Offer",
        "url": f"{url}?variante={v['sku']}",
        "price": f"{v['precio'] / 100:.2f}",
        "priceCurrency": "GTQ",
        "availability": "https://schema.org/InStock" if v["disponible"] else "https://schema.org/OutOfStock",
        "itemCondition": "https://schema.org/NewCondition",
        "shippingDetails": detalles_envio(),
    }


def detalles_envio() -> dict[str, Any]:
    envio = ENVIOS["estandar"]
    return {
        "@type": "OfferShippingDetails",
        "shippingRate": {"@type": "MonetaryAmount", "value": f"{envio['precio'] / 100:.2f}", "currency": "GTQ"},
        "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "GT"},
        "deliveryTime": {
            "@type": "ShippingDeliveryTime",
            "handlingTime": {"@type": "QuantitativeValue", "minValue": envio["preparacion"][0],
                             "maxValue": envio["preparacion"][1], "unitCode": "DAY"},
            "transitTime": {"@type": "QuantitativeValue", "minValue": envio["transito"][0],
                            "maxValue": envio["transito"][1], "unitCode": "DAY"},
            "businessDays": {
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": [f"https://schema.org/{d}" for d in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")],
            },
        },
    }
