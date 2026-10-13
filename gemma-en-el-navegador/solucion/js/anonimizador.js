// archivo: js/anonimizador.js
// Gemma encuentra los datos personales; el código arma el mapa y los reemplaza.
import { contiene, nuevoMarcador, plano, reemplazar } from './texto.js';

export const TIPOS = ['NOMBRE', 'DPI', 'NIT', 'TELEFONO', 'CORREO', 'DIRECCION', 'CUENTA', 'MONTO'];

const INSTRUCCIONES = `Eres un anonimizador. Lee el texto y lista TODOS los datos personales que aparecen: nombres y apellidos de personas, DPI, NIT, teléfonos, correos, direcciones, números de cuenta o póliza, y montos de dinero.
Responde solo con JSON, sin explicaciones, con esta forma:
{"datos":[{"tipo":"NOMBRE","valor":"..."}]}
Tipos permitidos: ${TIPOS.join(', ')}.
Copia cada valor exactamente como aparece en el texto. Incluye a todas las personas mencionadas (familiares, médicos, quien firma), aunque aparezcan solo con un nombre o un apellido. Si una persona aparece escrita de formas distintas, incluye cada forma. Incluye todos los montos.`;

// Corre en el navegador: una conversación nueva por texto, sin historial.
export async function buscarDatos(engine, texto) {
  const conversacion = await engine.createConversation({
    preface: { messages: [{ role: 'system', content: INSTRUCCIONES }] },
    // type 3 = GREEDY: el mismo texto da siempre la misma respuesta.
    sessionConfig: { maxOutputTokens: 1024, samplerParams: { type: 3 } },
  });
  try {
    const respuesta = await conversacion.sendMessage(texto);
    return leerDatos(respuesta.content.map((parte) => parte.text ?? '').join(''));
  } finally {
    await conversacion.delete();
  }
}

// Gemma a veces envuelve el JSON en ```json ... ```: tomamos de la primera { a la última }.
export function leerDatos(salida) {
  const inicio = salida.indexOf('{');
  const fin = salida.lastIndexOf('}');
  if (inicio < 0 || fin < inicio) throw new Error('Gemma no devolvió JSON.');
  const { datos } = JSON.parse(salida.slice(inicio, fin + 1));
  if (!Array.isArray(datos)) throw new Error('El JSON de Gemma no trae la lista "datos".');
  return datos;
}

// Convierte la lista de Gemma en { texto, mapa, ignorados }.
// Solo se usan valores que de verdad están en el texto: si Gemma inventa o
// cambia un valor, se ignora y el detector revisará lo que haya quedado.
export function armarMapa(texto, datos) {
  const mapa = {};
  const ignorados = [];
  const vistos = new Set();
  for (const { tipo, valor } of datos) {
    if (typeof valor !== 'string' || !valor.trim()) continue;
    const clave = plano(valor.trim());
    if (vistos.has(clave)) continue;
    if (!contiene(texto, valor)) {
      ignorados.push(valor);
      continue;
    }
    vistos.add(clave);
    mapa[nuevoMarcador(TIPOS.includes(tipo) ? tipo : 'DATO', mapa)] = valor.trim();
  }
  // Primero los valores largos: «Marta Pop de León» antes que «Marta».
  let limpio = texto;
  for (const [marcador, valor] of Object.entries(mapa).sort((a, b) => b[1].length - a[1].length)) {
    limpio = reemplazar(limpio, valor, marcador);
  }
  return { texto: limpio, mapa, ignorados };
}
