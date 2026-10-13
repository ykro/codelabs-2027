// Pruebas del mapa de marcadores (paso 4):
//   node --test pruebas/anonimizador.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { armarMapa, leerDatos } from '../js/anonimizador.js';

test('leerDatos acepta el JSON envuelto en ```json', () => {
  const salida = '```json\n{"datos":[{"tipo":"NOMBRE","valor":"Ana"}]}\n```';
  assert.deepEqual(leerDatos(salida), [{ tipo: 'NOMBRE', valor: 'Ana' }]);
  assert.throws(() => leerDatos('No encontré datos.'), /JSON/);
});

test('armarMapa reemplaza primero los valores largos e ignora lo que no está en el texto', () => {
  const texto = 'Yo soy Marta Pop de León. Firma: Marta.';
  const datos = [
    { tipo: 'NOMBRE', valor: 'Marta' },
    { tipo: 'NOMBRE', valor: 'Marta Pop de León' },
    { tipo: 'TELEFONO', valor: '5555-0000' },
  ];
  const { texto: limpio, mapa, ignorados } = armarMapa(texto, datos);
  assert.equal(limpio, 'Yo soy [NOMBRE_2]. Firma: [NOMBRE_1].');
  assert.deepEqual(mapa, { '[NOMBRE_1]': 'Marta', '[NOMBRE_2]': 'Marta Pop de León' });
  assert.deepEqual(ignorados, ['5555-0000']);
});
