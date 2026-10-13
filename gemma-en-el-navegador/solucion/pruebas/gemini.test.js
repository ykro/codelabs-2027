// La función que habla con la nube no abre la conexión si el texto tiene una fuga (paso 6):
//   node --test pruebas/gemini.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { preguntarAGemini } from '../js/gemini.js';

function fetchFalso(respuesta = { candidates: [{ content: { parts: [{ text: 'Hola [NOMBRE_1]' }] } }] }) {
  const llamadas = [];
  globalThis.fetch = async (url, opciones) => {
    llamadas.push({ url, opciones });
    return { ok: true, status: 200, json: async () => respuesta };
  };
  return llamadas;
}

const base = { llave: 'llave-de-prueba', modelo: 'gemini-3.8-flash', tarea: 'formal' };

test('con una fuga no hace ninguna solicitud', async () => {
  const llamadas = fetchFalso();
  await assert.rejects(
    preguntarAGemini({ ...base, texto: 'Soy [NOMBRE_1], mi DPI es 2456 78905 0101', mapa: {} }),
    /Bloqueado/,
  );
  assert.equal(llamadas.length, 0);
});

test('con un valor del mapa todavía en el texto no hace ninguna solicitud', async () => {
  const llamadas = fetchFalso();
  await assert.rejects(
    preguntarAGemini({ ...base, texto: 'Saludos de Ana Lucía Morales', mapa: { '[NOMBRE_1]': 'Ana Lucía Morales' } }),
    /Bloqueado/,
  );
  assert.equal(llamadas.length, 0);
});

test('con texto limpio envía solo marcadores y la llave va en el encabezado', async () => {
  const llamadas = fetchFalso();
  const mapa = { '[NOMBRE_1]': 'Ana Lucía Morales' };
  const respuesta = await preguntarAGemini({ ...base, texto: 'Soy [NOMBRE_1] y pido mi reembolso.', mapa });
  assert.equal(respuesta, 'Hola [NOMBRE_1]');
  assert.equal(llamadas.length, 1);
  const { url, opciones } = llamadas[0];
  assert.match(url, /models\/gemini-3\.8-flash:generateContent$/);
  assert.equal(opciones.headers['x-goog-api-key'], 'llave-de-prueba');
  assert.ok(!opciones.body.includes('Ana'));
  assert.ok(!url.includes('llave-de-prueba'));
});
