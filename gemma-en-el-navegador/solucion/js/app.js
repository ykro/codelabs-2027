// Interfaz de la página. Une los módulos que escribes en el taller:
// modelo.js (paso 3), anonimizador.js (paso 4), detector.js (paso 5),
// gemini.js (paso 6) y restaurar.js (paso 7).
import { borrarModelo, cargarGemma, estadoDescarga } from './modelo.js';
import { armarMapa, buscarDatos } from './anonimizador.js';
import { buscarFugas, cubrirFugas, revisarAMano } from './detector.js';
import { armarSolicitud, preguntarAGemini } from './gemini.js';
import { restaurar } from './restaurar.js';
import { EJEMPLOS } from './ejemplos.js';

const $ = (id) => document.getElementById(id);
const MODELO_GEMINI = 'gemini-3.8-flash';
const estado = { engine: null, limpio: '', mapa: {}, revision: null, ocupado: false };

// ---------- utilidades de interfaz ----------
const segundos = (desde) => ((performance.now() - desde) / 1000).toFixed(1);

function leerLocal(clave) {
  try { return localStorage.getItem(clave) ?? ''; } catch { return ''; }
}
function guardarLocal(clave, valor) {
  try { localStorage.setItem(clave, valor); } catch { /* sin almacenamiento: se usa solo en esta pestaña */ }
}

function escapar(texto) {
  return texto.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}
function conMarcadores(texto) {
  return escapar(texto).replace(/\[[A-Z]+_\d+\]/g, (m) => `<span class="marcador">${m}</span>`);
}
function mensajeError(error) {
  return error?.message ?? String(error);
}

function actualizarBotones() {
  const llave = $('llave').value.trim();
  $('proteger').disabled = !estado.engine || estado.ocupado;
  $('enviar').disabled = !estado.revision?.ok || !llave || estado.ocupado;
  $('enviar').title = !llave ? 'Escribe tu llave de AI Studio' : '';
}

function limpiarEtapas() {
  estado.limpio = '';
  estado.mapa = {};
  estado.revision = null;
  $('mapa').className = 'vacio';
  $('mapa').textContent = 'Aquí verás lo que Gemma encontró.';
  $('veredicto').replaceChildren();
  $('limpio').className = 'texto vacio';
  $('limpio').textContent = 'Aquí verás el único texto que puede salir.';
  $('revisar').textContent = '';
  $('cubrir').hidden = true;
  $('solicitud').hidden = true;
  $('respuesta-nube').replaceChildren();
  $('final').className = 'texto vacio';
  $('final').textContent = 'Aquí verás la respuesta con tus datos.';
  $('copiar').hidden = true;
  $('copiar').textContent = 'Copiar respuesta';
  actualizarBotones();
}

// ---------- 1. preparar ----------
async function revisarEntorno() {
  const webgpu = $('estado-webgpu');
  const adaptador = navigator.gpu ? await navigator.gpu.requestAdapter().catch(() => null) : null;
  if (adaptador) {
    webgpu.textContent = 'WebGPU disponible: Gemma puede correr en este navegador.';
    webgpu.className = 'estado bien';
  } else {
    webgpu.textContent = 'Este navegador no ofrece WebGPU. Usa Chrome o Edge recientes en una computadora.';
    webgpu.className = 'estado mal';
    $('estado-modelo').textContent = 'Sin WebGPU no se puede cargar Gemma.';
    return;
  }
  try {
    await mostrarEstadoDescarga();
  } catch (error) {
    $('estado-modelo').textContent = mensajeError(error);
    return;
  }
  $('cargar').disabled = false;
}

const gb = (bytes) => (bytes / 1e9).toFixed(2);

async function mostrarEstadoDescarga() {
  const { completo, guardados, total } = await estadoDescarga();
  if (completo) {
    $('estado-modelo').textContent = `Ya está guardado en este navegador (${gb(total)} GB). Se carga sin descargar.`;
    $('cargar').textContent = 'Cargar Gemma';
  } else if (guardados) {
    $('estado-modelo').textContent = `Descarga a medias: ${gb(guardados)} de ${gb(total)} GB guardados. Pulsa el botón para continuar donde quedó.`;
    $('cargar').textContent = 'Continuar la descarga';
  } else {
    $('estado-modelo').textContent = 'Se descarga una sola vez (2 GB) y queda guardado en este navegador.';
    $('cargar').textContent = 'Descargar y cargar Gemma';
  }
}

async function prepararGemma(archivo) {
  const boton = $('cargar');
  const progreso = $('progreso');
  boton.disabled = true;
  const inicio = performance.now();
  try {
    $('estado-modelo').textContent = archivo ? `Leyendo ${archivo.name}…` : 'Preparando…';
    let nota = '';
    const { engine, origen, persistente } = await cargarGemma({
      archivo,
      alAvanzar: ({ recibidos, total, continua, reinicio }) => {
        if (continua) nota = ' · continúa donde quedó';
        if (reinicio) nota = ' · el servidor no permitió continuar: empezó de cero';
        progreso.hidden = false;
        progreso.value = total ? recibidos / total : 0;
        $('estado-modelo').textContent = `Descargando: ${gb(recibidos)} de ${gb(total)} GB (${segundos(inicio)} s)${nota}`;
      },
    });
    progreso.hidden = true;
    const cargado = segundos(inicio);
    $('estado-modelo').textContent = `Modelo listo (${origen}, ${cargado} s). Calentando…`;
    // La primera respuesta compila el modelo para tu GPU; después todo es más rápido.
    const prueba = performance.now();
    const conversacion = await engine.createConversation();
    const saludo = await conversacion.sendMessage('Responde solo con la palabra: lista');
    await conversacion.delete();
    estado.engine = engine;
    const palabra = saludo.content.map((parte) => parte.text ?? '').join('').trim();
    const guardado = persistente ? 'Guardado persistente: sí.' : 'Guardado persistente: no (el navegador podría borrarlo si le falta espacio).';
    $('estado-modelo').textContent = `Gemma lista. Origen: ${origen}. Carga: ${cargado} s. Primera respuesta («${palabra}»): ${segundos(prueba)} s. ${guardado}`;
    $('estado-modelo').className = 'estado bien';
    boton.textContent = 'Gemma cargada';
  } catch (error) {
    progreso.hidden = true;
    boton.disabled = false;
    const { guardados } = await estadoDescarga().catch(() => ({ guardados: 0 }));
    const seguir = guardados && !archivo ? ` Ya hay ${gb(guardados)} GB guardados: pulsa «Continuar la descarga».` : '';
    $('estado-modelo').textContent = `No se pudo cargar Gemma (${mensajeError(error)}).${seguir}`;
    $('estado-modelo').className = 'estado mal';
    if (seguir) boton.textContent = 'Continuar la descarga';
  }
  actualizarBotones();
}

// ---------- 2. proteger (todo en tu dispositivo) ----------
function mostrarMapa(mapa, ignorados, tiempo) {
  const filas = Object.entries(mapa)
    .map(([marcador, valor]) => `<tr><td><span class="marcador">${escapar(marcador)}</span></td><td>${escapar(valor)}</td></tr>`)
    .join('');
  const contenedor = $('mapa');
  contenedor.className = '';
  contenedor.innerHTML = filas
    ? `<table class="tabla"><thead><tr><th>Marcador</th><th>Dato real</th></tr></thead><tbody>${filas}</tbody></table>`
    : '<p class="aviso">Gemma no encontró datos personales.</p>';
  const pie = [`Gemma tardó ${tiempo} s. Este mapa nunca sale de tu dispositivo.`];
  if (ignorados.length) pie.push(`Ignorados (no están en el texto): ${ignorados.join(', ')}.`);
  contenedor.insertAdjacentHTML('beforeend', `<p class="nota">${escapar(pie.join(' '))}</p>`);
}

function mostrarRevision() {
  const { revision, limpio } = estado;
  $('limpio').className = 'texto';
  $('limpio').innerHTML = conMarcadores(limpio);
  const veredicto = $('veredicto');
  if (revision.ok) {
    veredicto.innerHTML = '<div class="veredicto bien"><strong>El detector aprobó el texto</strong>No quedó ningún dato personal que el código pueda reconocer. Puede salir.</div>';
  } else {
    const lista = revision.fugas
      .map((f) => `<li><b>${escapar(f.tipo)}</b>: ${escapar(f.valor)} <span class="nota">(${escapar(f.motivo)})</span></li>`)
      .join('');
    veredicto.innerHTML = `<div class="veredicto mal"><strong>Bloqueado: no se enviará nada</strong>El detector encontró ${revision.fugas.length} dato(s) que Gemma dejó pasar:<ul>${lista}</ul><p class="nota">Esta lista se queda en tu dispositivo.</p></div>`;
  }
  $('cubrir').hidden = revision.ok;
  const encontradas = new Set(revision.fugas.map((f) => f.valor));
  const dudosas = revisarAMano(limpio).filter((p) => !encontradas.has(p));
  $('revisar').textContent = dudosas.length
    ? `Revisa a mano antes de enviar (palabras con mayúscula que podrían ser nombres): ${dudosas.join(', ')}.`
    : '';
  actualizarBotones();
}

async function proteger() {
  const texto = $('texto').value.normalize('NFC').trim();
  if (!texto) return;
  limpiarEtapas();
  estado.ocupado = true;
  actualizarBotones();
  $('estado-proteger').textContent = 'Gemma está buscando datos personales en tu dispositivo…';
  const inicio = performance.now();
  try {
    const datos = await buscarDatos(estado.engine, texto);
    const tiempo = segundos(inicio);
    const { texto: limpio, mapa, ignorados } = armarMapa(texto, datos);
    estado.limpio = limpio;
    estado.mapa = mapa;
    mostrarMapa(mapa, ignorados, tiempo);
    $('limpio').className = 'texto';
    $('limpio').innerHTML = conMarcadores(limpio);
    estado.revision = buscarFugas(limpio, mapa);
    mostrarRevision();
    document.querySelector('.etapas').scrollIntoView({ behavior: 'smooth', block: 'start' });
    $('estado-proteger').textContent = estado.revision.ok
      ? 'Listo. Revisa el texto limpio y envíalo a Gemini.'
      : 'El detector bloqueó el envío. Puedes cubrir lo que encontró o editar tu texto.';
  } catch (error) {
    $('estado-proteger').textContent = `No se pudo proteger el texto: ${mensajeError(error)}`;
    $('veredicto').innerHTML = `<div class="veredicto mal"><strong>No se enviará nada</strong>${escapar(mensajeError(error))}</div>`;
  } finally {
    estado.ocupado = false;
    actualizarBotones();
  }
}

function cubrir() {
  const { texto, mapa } = cubrirFugas(estado.limpio, estado.mapa, estado.revision.fugas);
  estado.limpio = texto;
  estado.mapa = mapa;
  mostrarMapa(mapa, [], '—');
  estado.revision = buscarFugas(texto, mapa);
  mostrarRevision();
}

// ---------- 3. enviar y restaurar ----------
async function enviar() {
  const llave = $('llave').value.trim();
  const modelo = $('modelo').value.trim() || MODELO_GEMINI;
  const tarea = $('tarea').value;
  estado.ocupado = true;
  actualizarBotones();
  const respuestaNube = $('respuesta-nube');
  respuestaNube.innerHTML = `<p class="nota">Esperando a ${escapar(modelo)}…</p>`;
  let respuesta;
  const inicio = performance.now();
  try {
    $('solicitud').querySelector('pre').textContent = JSON.stringify(armarSolicitud(tarea, estado.limpio), null, 2);
    $('solicitud').hidden = false;
    respuesta = await preguntarAGemini({ llave, modelo, tarea, texto: estado.limpio, mapa: estado.mapa });
    respuestaNube.innerHTML = `<h3>Respuesta de Gemini (${segundos(inicio)} s)</h3><pre class="texto">${conMarcadores(respuesta)}</pre>`;
  } catch (error) {
    respuestaNube.innerHTML = `<div class="veredicto mal"><strong>No hubo respuesta</strong>${escapar(mensajeError(error))}</div>`;
  }
  if (respuesta !== undefined) {
    try {
      const final = restaurar(respuesta, estado.mapa);
      $('final').className = 'texto';
      $('final').textContent = final.texto;
      $('copiar').hidden = false;
      if (final.sinRestaurar.length) {
        respuestaNube.insertAdjacentHTML('beforeend', `<p class="aviso">Gemini usó marcadores que no están en tu mapa: ${escapar(final.sinRestaurar.join(', '))}.</p>`);
      }
    } catch (error) {
      $('final').textContent = mensajeError(error);
    }
  }
  estado.ocupado = false;
  actualizarBotones();
}

// ---------- arranque ----------
function iniciar() {
  for (const [i, ejemplo] of EJEMPLOS.entries()) $('ejemplo').add(new Option(ejemplo.titulo, String(i)));
  $('texto').value = EJEMPLOS[0].texto;
  $('llave').value = leerLocal('gemini-llave');
  $('modelo').value = leerLocal('gemini-modelo') || MODELO_GEMINI;

  $('ejemplo').addEventListener('change', () => {
    $('texto').value = EJEMPLOS[Number($('ejemplo').value)].texto;
    limpiarEtapas();
  });
  $('texto').addEventListener('input', limpiarEtapas);
  $('llave').addEventListener('input', () => {
    guardarLocal('gemini-llave', $('llave').value.trim());
    actualizarBotones();
  });
  $('modelo').addEventListener('change', () => guardarLocal('gemini-modelo', $('modelo').value.trim()));
  $('ver-llave').addEventListener('click', () => {
    const ver = $('llave').type === 'password';
    $('llave').type = ver ? 'text' : 'password';
    $('ver-llave').textContent = ver ? 'Ocultar' : 'Mostrar';
    $('ver-llave').setAttribute('aria-pressed', String(ver));
  });
  $('cargar').addEventListener('click', () => prepararGemma());
  $('archivo').addEventListener('change', () => {
    const archivo = $('archivo').files[0];
    if (archivo) prepararGemma(archivo);
  });
  $('borrar').addEventListener('click', async () => {
    await borrarModelo().catch(() => {});
    $('estado-modelo').className = 'nota';
    $('estado-modelo').textContent = 'Modelo borrado de este navegador. Se descargará de nuevo si lo cargas.';
    if (!estado.engine) $('cargar').textContent = 'Descargar y cargar Gemma';
  });
  $('proteger').addEventListener('click', proteger);
  $('cubrir').addEventListener('click', cubrir);
  $('enviar').addEventListener('click', enviar);
  $('copiar').addEventListener('click', async () => {
    await navigator.clipboard.writeText($('final').textContent).catch(() => {});
    $('copiar').textContent = 'Copiada';
  });
  actualizarBotones();
  revisarEntorno();
}

iniciar();
