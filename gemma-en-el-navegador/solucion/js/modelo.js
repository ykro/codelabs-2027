// archivo: js/modelo.js
// Gemma 4 E2B en tu navegador con LiteRT-LM Web (WebGPU).
// El archivo (2 GB) se descarga una vez, por partes, al almacenamiento privado del
// navegador (OPFS). Si la descarga se corta, la siguiente vez pide solo lo que falta.
import { Engine } from 'https://cdn.jsdelivr.net/npm/@litert-lm/core@0.18.0/+esm';

export const MODELO_URL =
  'https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm/resolve/main/gemma-4-E2B-it-web.litertlm';
const PREFIJO = 'gemma-4-E2B-it-web';
const PARTE = 32 * 1024 * 1024; // 32 MB por archivo: si se corta, se pierde como mucho una parte
const nombreParte = (i) => `${PREFIJO}.parte-${String(i).padStart(4, '0')}`;

const carpeta = () => navigator.storage.getDirectory();

async function leerInfo() {
  try {
    const archivo = await (await (await carpeta()).getFileHandle(`${PREFIJO}.json`)).getFile();
    return JSON.parse(await archivo.text());
  } catch {
    return null;
  }
}

async function guardarInfo(info) {
  const escritor = await (await (await carpeta()).getFileHandle(`${PREFIJO}.json`, { create: true })).createWritable();
  await escritor.write(JSON.stringify(info));
  await escritor.close();
}

// Partes completas guardadas, en orden. Una parte solo existe si se cerró entera.
async function partesGuardadas() {
  const dir = await carpeta();
  const partes = [];
  for (let i = 0; ; i++) {
    try {
      partes.push(await (await dir.getFileHandle(nombreParte(i))).getFile());
    } catch {
      return partes;
    }
  }
}

// { completo, guardados, total }: lo que la página muestra antes de cargar.
export async function estadoDescarga() {
  const info = await leerInfo();
  const guardados = (await partesGuardadas()).reduce((suma, parte) => suma + parte.size, 0);
  return { completo: Boolean(info?.completo && guardados === info.total), guardados, total: info?.total ?? 0 };
}

async function escribirParte(i, trozos) {
  const escritor = await (await (await carpeta()).getFileHandle(nombreParte(i), { create: true })).createWritable();
  await escritor.write(new Blob(trozos));
  await escritor.close(); // hasta aquí la parte no existe: un corte nunca deja una parte a medias
}

async function descargar(alAvanzar) {
  let info = await leerInfo();
  let partes = (await partesGuardadas()).filter((p) => p.size === PARTE);
  let desde = partes.length * PARTE;
  const respuesta = await fetch(MODELO_URL, desde ? { headers: { Range: `bytes=${desde}-` } } : {});
  const etag = respuesta.headers.get('etag');
  let continua = respuesta.status === 206;
  // Solo se continúa si el servidor mandó el resto (206) del mismo archivo (mismo ETag).
  if (desde && (!continua || (info?.etag && etag !== info.etag))) {
    await borrarModelo();
    if (respuesta.status === 206) {
      await respuesta.body.cancel(); // el archivo cambió en el servidor: de cero
      return descargar(alAvanzar);
    }
    desde = 0;
    continua = false;
  }
  if (!respuesta.ok) throw new Error(`No se pudo descargar el modelo (HTTP ${respuesta.status}).`);
  const rango = respuesta.headers.get('content-range'); // «bytes 1000-2008432639/2008432640»
  const total = rango ? Number(rango.split('/')[1]) : Number(respuesta.headers.get('content-length'));
  info = { url: MODELO_URL, total, etag, completo: false };
  await guardarInfo(info);

  let indice = desde / PARTE;
  let recibidos = desde;
  let trozos = [];
  let enMemoria = 0;
  const lector = respuesta.body.getReader();
  alAvanzar?.({ recibidos, total, continua, reinicio: Boolean(desde === 0 && partes.length) });
  for (;;) {
    const { done, value } = await lector.read();
    if (value) {
      trozos.push(value);
      enMemoria += value.length;
      recibidos += value.length;
    }
    while (enMemoria >= PARTE || (done && enMemoria > 0)) {
      const todo = new Blob(trozos);
      const largo = Math.min(PARTE, enMemoria);
      await escribirParte(indice++, [todo.slice(0, largo)]);
      trozos = [todo.slice(largo)];
      enMemoria -= largo;
    }
    alAvanzar?.({ recibidos, total, continua });
    if (done) break;
  }
  partes = await partesGuardadas();
  const guardados = partes.reduce((suma, parte) => suma + parte.size, 0);
  if (guardados !== total) throw new Error(`La descarga quedó incompleta (${guardados} de ${total} bytes). Vuelve a intentar.`);
  await guardarInfo({ ...info, completo: true });
  return new Blob(partes); // las partes se leen en orden, sin copiarlas a memoria
}

export async function modeloGuardado() {
  const estado = await estadoDescarga();
  return estado.completo ? new Blob(await partesGuardadas()) : null;
}

// archivo: un File elegido desde el disco (opcional). Si no hay, usa el guardado o lo descarga.
export async function cargarGemma({ archivo, alAvanzar } = {}) {
  if (!('gpu' in navigator)) throw new Error('Este navegador no tiene WebGPU.');
  const persistente = (await navigator.storage.persist?.()) ?? false; // que el navegador no lo borre
  let modelo = archivo ?? (await modeloGuardado());
  const origen = archivo ? 'disco' : modelo ? 'guardado' : 'descarga';
  if (!modelo) modelo = await descargar(alAvanzar);
  const engine = await Engine.create({ model: modelo, mainExecutorSettings: { maxNumTokens: 4096 } });
  return { engine, origen, persistente };
}

export async function borrarModelo() {
  const dir = await carpeta();
  const nombres = [];
  for await (const nombre of dir.keys()) if (nombre.startsWith(PREFIJO)) nombres.push(nombre);
  for (const nombre of nombres) await dir.removeEntry(nombre);
}
