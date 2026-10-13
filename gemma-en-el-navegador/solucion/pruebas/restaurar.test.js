// Pruebas de la restauración (paso 7):
//   node --test pruebas/restaurar.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buscarFugas, cubrirFugas } from '../js/detector.js';
import { restaurar } from '../js/restaurar.js';

test('cubrirFugas deja el texto aprobado y el mapa puede restaurarlo', () => {
  const mapa = { '[NOMBRE_1]': 'Carlos Enrique Xitumul Coc' };
  const texto = 'Soy [NOMBRE_1]. Mi teléfono es 4021-8890. Atentamente, Carlos Xitumul.';
  const cubierto = cubrirFugas(texto, mapa, buscarFugas(texto, mapa).fugas);
  assert.equal(buscarFugas(cubierto.texto, cubierto.mapa).ok, true);
  assert.equal(restaurar(cubierto.texto, cubierto.mapa).texto, texto.replace('[NOMBRE_1]', 'Carlos Enrique Xitumul Coc'));
});

test('restaurar devuelve los datos y avisa de marcadores inventados', () => {
  const mapa = { '[NOMBRE_1]': 'Ana Lucía Morales', '[MONTO_1]': 'Q650' };
  const { texto, sinRestaurar } = restaurar('Estimada [NOMBRE_1]: su reembolso de [MONTO_1] y [MONTO_7].', mapa);
  assert.equal(texto, 'Estimada Ana Lucía Morales: su reembolso de Q650 y [MONTO_7].');
  assert.deepEqual(sinRestaurar, ['[MONTO_7]']);
});
