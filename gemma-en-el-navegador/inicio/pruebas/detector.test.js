// Pruebas del detector (paso 5). Corren en Node, sin navegador:
//   node --test pruebas/detector.test.js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buscarFugas, dpiValido, revisarAMano } from '../js/detector.js';
import { EJEMPLOS } from '../js/ejemplos.js';

const tipos = (texto, mapa) => buscarFugas(texto, mapa).fugas.map((f) => f.tipo);

test('dpiValido acepta un DPI con dígito verificador correcto y rechaza uno alterado', () => {
  assert.equal(dpiValido('2456 78905 0101'), true);
  assert.equal(dpiValido('1987654360101'), true);
  assert.equal(dpiValido('2456 78901 0101'), false); // verificador equivocado
  assert.equal(dpiValido('2456 78905 2301'), false); // departamento 23 no existe
});

test('detecta cada formato de dato personal', () => {
  assert.deepEqual(tipos('escríbeme a ana.lopez@ejemplo.com'), ['CORREO']);
  assert.deepEqual(tipos('DPI 2456 78905 0101'), ['DPI']);
  assert.deepEqual(tipos('NIT 7766554-K'), ['NIT']);
  assert.deepEqual(tipos('llámame al 5512-3478'), ['TELEFONO']);
  assert.deepEqual(tipos('o al +502 4021 8890'), ['TELEFONO']);
  assert.deepEqual(tipos('me cobraron Q2,500.00'), ['MONTO']);
  assert.deepEqual(tipos('son 350 quetzales'), ['MONTO']);
  assert.deepEqual(tipos('vivo en 13 calle 5-20 zona 10'), ['DIRECCION']);
  assert.deepEqual(tipos('cuenta 301-0045872-1'), ['NUMERO']);
  assert.deepEqual(tipos('la consulta del Dr. Ramírez'), ['NOMBRE']);
  assert.deepEqual(tipos('Don Julio dejó todo'), ['NOMBRE']);
});

test('un título seguido de un marcador no es una fuga', () => {
  assert.equal(buscarFugas('la consulta del Dr. [NOMBRE_2] y doña [NOMBRE_1]').ok, true);
});

test('el DPI se reporta una vez, no también como teléfono', () => {
  const { fugas } = buscarFugas('DPI 2456 78905 0101');
  assert.equal(fugas.length, 1);
  assert.equal(fugas[0].motivo, 'DPI con dígito verificador válido');
});

test('no confunde fechas, horas ni números cortos con datos', () => {
  assert.equal(buscarFugas('El 3 de septiembre de 2026 a las 10:30, en la zona 10, pagué 2 cuotas.').ok, true);
});

test('cada texto de ejemplo sin proteger tiene fugas', () => {
  for (const { titulo, texto } of EJEMPLOS) {
    assert.equal(buscarFugas(texto).ok, false, titulo);
  }
});

test('el texto limpio con marcadores pasa', () => {
  const limpio = 'Soy [NOMBRE_1], DPI [DPI_1]. Me cobraron [MONTO_1]. Llámenme al [TELEFONO_1].';
  assert.equal(buscarFugas(limpio, { '[NOMBRE_1]': 'María José Pérez Ajú' }).ok, true);
});

test('bloquea un valor del mapa que siguió en el texto, sin importar tildes ni mayúsculas', () => {
  const mapa = { '[NOMBRE_1]': 'María José Pérez Ajú' };
  const { ok, fugas } = buscarFugas('Saludos, MARIA JOSE PEREZ AJU', mapa);
  assert.equal(ok, false);
  assert.equal(fugas[0].marcador, '[NOMBRE_1]');
});

test('bloquea partes de un nombre conocido: la firma «Carlos Xitumul»', () => {
  const mapa = { '[NOMBRE_1]': 'Carlos Enrique Xitumul Coc' };
  const { fugas } = buscarFugas('Atentamente, Carlos Xitumul.', mapa);
  assert.deepEqual(fugas.map((f) => f.valor), ['Carlos', 'Xitumul']);
});

test('una parte de nombre corta no coincide dentro de otra palabra', () => {
  const mapa = { '[NOMBRE_1]': 'Ana Coc' };
  assert.equal(buscarFugas('Mariana llegó mañana', mapa).ok, true);
});

test('revisarAMano señala nombres que el código no puede reconocer', () => {
  assert.deepEqual(revisarAMano('Si no contestan, mi hija Sofía responde. Gracias.'), ['Sofía']);
  assert.deepEqual(revisarAMano('la consulta del Dr. [NOMBRE_2]'), []);
});
