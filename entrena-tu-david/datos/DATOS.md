# Datos: mensajes de Ferretería La Ceiba

Mensajes de WhatsApp de clientes de una ferretería ficticia de Guatemala, cada uno con el ticket JSON correcto. Son el material del taller «Entrena a tu propio David».

| Archivo | Registros | Uso |
|---|---|---|
| `train.jsonl` | 1000 | entrenar el adaptador LoRA |
| `test.jsonl` | 150 | medir; **nunca** se usa para entrenar |
| `generar_datos.py` | — | el script que generó y validó los dos archivos |
| `estadisticas.json` | — | cuántos mensajes se pidieron, cuántos pasaron y por qué se rechazó el resto |

Licencia de los datos: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.es). Puedes copiarlos, cambiarlos y usarlos para lo que quieras, citando la fuente («Codelabs 2027, Entrena a tu propio David»).

## Formato

Una línea JSON por registro:

```json
{"id": "train-0001",
 "mensaje": "Buenas tardes, mire que chilero su servicio, tráigame 15 palas para el sabado por favor, ahí el patojo va a estar esperando para recibirlas.",
 "ticket": {"tipo": "pedido", "categoria": "herramientas", "producto": "pala", "cantidad": 15, "monto_q": null, "urgencia": "media"},
 "origen": {"tipo": "sintetico", "modelo": "gemini-3.8-flash", "servicio": "Vertex AI", "fecha": "2026-10-13",
            "semilla": 1821, "solicitud": "train-1821-00001", "pistas": {"...": "..."},
            "validacion": "reglas de generar_datos.py: ok"}}
```

El ticket tiene 6 campos fijos:

| Campo | Valores |
|---|---|
| `tipo` | `pedido`, `cotizacion`, `reclamo`, `seguimiento` |
| `categoria` | `obra_gris`, `techos`, `plomeria`, `electricidad`, `pintura`, `herramientas`, `jardin` |
| `producto` | nombre del producto en el catálogo de la tienda (43 productos, por ejemplo `varilla 3/8`, `tubo pvc 1/2`, `cinta teflón`) |
| `cantidad` | entero, o `null` si el cliente no la dice |
| `monto_q` | quetzales que menciona el cliente (pagó, le cobraron, tiene para gastar), o `null` |
| `urgencia` | `alta`, `media`, `baja` |

## Las reglas propias de la tienda

Esto es lo que un modelo general no sabe y el modelo ajustado aprende de los ejemplos:

- **Catálogo**: el producto se escribe con el nombre de la tienda, en singular. «3 varillas de tres octavos» → `varilla 3/8`; «tubos de media» → `tubo pvc 1/2`; «breakers» → `flipón`; «pintura de agua» o «latex» → `pintura de agua`.
- **Categorías de la tienda**: el clavo de 3 pulgadas y el alambre de amarre son `obra_gris`; los tornillos para lámina son `techos`; el pegamento PVC y el teflón son `plomeria`; la cinta de aislar es `electricidad`; la masilla y el thinner son `pintura`; la carretilla y la pala son `herramientas`; el machete, el azadón y la tijera de podar son `jardin`.
- **Urgencia**: `alta` = hoy o emergencia («para hoy», «ahorita mismo», «la obra está parada», «tengo una fuga»); `media` = con fecha en los próximos días («para mañana», «para el sábado», «esta semana»); `baja` = sin fecha («sin prisa», «solo estoy cotizando», «para el otro mes»).
- **Modismos**: «un par» = 2, «media docena» = 6, «una docena» = 12, «un ciento» = 100; «varos», «pesos» y «quetzalitos» son quetzales.

## Cómo se generó

1. **El código decide la respuesta primero.** `generar_datos.py` sortea cada ticket: tipo, producto del catálogo (con su categoría), cantidad, monto (dentro del rango de precio del producto) y urgencia. También sortea las pistas para escribir el mensaje: cómo decir la cantidad («media docena», «15», «quince»), cómo decir el monto («Q350», «350 varos», «350 pesos»), una frase de urgencia de la tabla de arriba y un estilo de chat guatemalteco («usa vos», «sin tildes», «usa patojo», «un emoji»…).
2. **Gemini escribe el mensaje.** `gemini-3.8-flash` en Vertex AI recibe 15 especificaciones por solicitud y escribe un mensaje informal por cada una, con las frases pedidas y sin otros números ni productos.
   Las frases de urgencia se sortean entre las que tienen sentido para ese ticket: «solo estoy cotizando» solo en cotizaciones, «tengo una fuga» solo con productos de plomería o jardín, «me quedé sin luz» solo con electricidad.
3. **Reglas en código validan cada mensaje.** Un mensaje se descarta si:
   - no nombra el producto con una de sus palabras, o nombra otro producto del catálogo;
   - no trae la cantidad pedida tal cual, o el monto no aparece como número;
   - trae números que no son la cantidad, el monto ni la medida del producto (teléfonos, horas, fechas);
   - menciona dinero cuando el ticket no tiene monto;
   - no trae la frase de urgencia pedida, o trae señales de otro nivel (por ejemplo «me urge» en un mensaje de urgencia `media`);
   - no tiene sentido con su ticket: habla de cotizar y no es una cotización, de una fuga y no es de plomería o jardín, o de quedarse sin luz y no es de electricidad;
   - no tiene ninguna palabra típica de su tipo (para un reclamo: «malo», «quebrado», «me cobraron de más»…);
   - mide menos de 25 o más de 300 caracteres, o repite un mensaje ya aceptado.
4. **Train y test por separado.** El test se generó primero, con su propia semilla (2027); el train después, con otra (1821). Un mensaje igual (sin contar mayúsculas, tildes ni espacios) no puede estar en los dos.

Resultado de la generación del 2026-10-13 (también en `estadisticas.json`):

| | Pedidos a Gemini | Aceptados | Rechazados y motivo principal |
|---|---|---|---|
| train | 1305 | 1000 | 38 sin palabra del tipo, 32 urgencia mezclada, 5 otros; el resto no se usó al llegar a 1000 |
| test | 200 | 150 | 10 sin palabra del tipo, 4 urgencia mezclada, 1 sin la frase de urgencia; el resto no se usó al llegar a 150 |

Una versión anterior (2026-10-12) sorteaba la frase de urgencia sin mirar el tipo ni el producto: 79 mensajes de train y 8 de test no tenían sentido («quiero 20 martillos, solo estoy cotizando»). Se agregaron la regla de coherencia y el sorteo de frases que cuadran, y se regeneró todo con las mismas semillas.

Cada registro guarda en `origen` el modelo, la fecha, la semilla, el identificador de la solicitud y las pistas que se le dieron a Gemini, así que cualquier mensaje se puede rastrear hasta su sorteo.

## Regenerarlos

```bash
GOOGLE_CLOUD_PROJECT=<tu-proyecto> uv run datos/generar_datos.py --train 1000 --test 150
```

Necesitas un proyecto de Google Cloud con Vertex AI y `gcloud auth application-default login`. Gemini escribe distinto cada vez, así que los mensajes cambian; las reglas y el reparto de tickets se mantienen.

## Límites

- Son mensajes sintéticos: Gemini imita el habla guatemalteca, pero no son conversaciones de clientes. Antes de usar un modelo así en una tienda, mídelo con mensajes de tus clientes.
- Cada mensaje pide un solo producto. Pedidos con varios productos quedan fuera del esquema.
- El test sale del mismo proceso que el train. Mide si el modelo aprendió las reglas de la tienda, no qué tan bien se las arregla con mensajes muy distintos.
- La regla de coherencia revisa el tipo y la categoría, no cada producto. Quedan unos pocos mensajes raros, por ejemplo una «fuga» junto a herramientas de jardín (9 de 1000 en train). Son ruido pequeño; si amplías el dataset, agrega una regla por producto.
