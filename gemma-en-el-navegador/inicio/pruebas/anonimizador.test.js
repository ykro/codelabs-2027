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

test('armarMapa guarda cada dato tal como está escrito', () => {
  const { texto, mapa } = armarMapa('Soy Ana Coc. Firma: ANA COC.', [{ tipo: 'NOMBRE', valor: 'ana coc' }]);
  assert.equal(texto, 'Soy [NOMBRE_1]. Firma: [NOMBRE_2].');
  assert.deepEqual(mapa, { '[NOMBRE_1]': 'Ana Coc', '[NOMBRE_2]': 'ANA COC' });
});

test('armarMapa no deja en el mapa un valor que solo estaba dentro de otro', () => {
  const datos = [{ tipo: 'CORREO', valor: 'marta.leon@ejemplo.com' }, { tipo: 'NOMBRE', valor: 'León' }];
  const { texto, mapa } = armarMapa('Soy Marta León, correo marta.leon@ejemplo.com', datos);
  assert.equal(texto, 'Soy Marta [NOMBRE_1], correo [CORREO_1]');
  assert.deepEqual(mapa, { '[CORREO_1]': 'marta.leon@ejemplo.com', '[NOMBRE_1]': 'León' });
});
