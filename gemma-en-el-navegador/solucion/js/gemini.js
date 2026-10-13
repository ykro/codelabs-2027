// archivo: js/gemini.js
// La única función que habla con la nube. Antes de abrir la conexión vuelve a
// pasar el detector sobre el texto exacto que va a enviar: si hay una fuga, no sale nada.
import { buscarFugas } from './detector.js';

export const TAREAS = {
  formal: 'Reescribe este mensaje como un correo formal, claro y breve, listo para enviar.',
  pedir: 'Resume el caso en tres puntos y dime qué debo pedir y qué documentos preparar.',
};

const INSTRUCCIONES = 'Los datos personales vienen como marcadores entre corchetes, por ejemplo [NOMBRE_1] o [DPI_1]. Copia cada marcador exactamente igual donde lo necesites. No inventes datos ni marcadores nuevos. Responde en español de Guatemala, en texto simple sin formato Markdown.';

export function armarSolicitud(tarea, texto) {
  return {
    systemInstruction: { parts: [{ text: INSTRUCCIONES }] },
    contents: [{ role: 'user', parts: [{ text: `${TAREAS[tarea]}\n\n${texto}` }] }],
  };
}

export async function preguntarAGemini({ llave, modelo, tarea, texto, mapa }) {
  const revision = buscarFugas(texto, mapa);
  if (!revision.ok) {
    throw new Error(`Bloqueado: el texto todavía tiene ${revision.fugas.length} dato(s) personal(es). No se envió nada.`);
  }
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(modelo)}:generateContent`;
  const respuesta = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-goog-api-key': llave },
    body: JSON.stringify(armarSolicitud(tarea, texto)),
  });
  const datos = await respuesta.json().catch(() => ({}));
  if (respuesta.status === 429) {
    throw new Error('Llegaste al límite de tu cuota gratuita. Espera o cambia el modelo (por ejemplo gemini-3.5-flash-lite).');
  }
  if (!respuesta.ok) throw new Error(datos.error?.message ?? `Gemini respondió HTTP ${respuesta.status}.`);
  return (datos.candidates?.[0]?.content?.parts ?? []).map((parte) => parte.text ?? '').join('').trim();
}
