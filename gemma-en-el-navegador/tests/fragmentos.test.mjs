// Cada bloque de código del codelab marcado con «// archivo: <ruta>» aparece textual en solucion/<ruta>,
// y el comando de cada prueba que menciona el codelab existe.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const taller = join(dirname(fileURLToPath(import.meta.url)), '..');
const md = readFileSync(join(taller, 'codelab.md'), 'utf8');
const bloques = [...md.matchAll(/^```(\w+)\n([\s\S]*?)^```$/gm)].map((m) => ({ lang: m[1], code: m[2] }));
const deArchivo = bloques.filter((b) => b.code.startsWith('// archivo: '));

test('el codelab tiene los cinco archivos que escribe el alumno', () => {
  const rutas = deArchivo.map((b) => b.code.split('\n')[0].slice(12).trim());
  assert.deepEqual(rutas, ['js/modelo.js', 'js/anonimizador.js', 'js/detector.js', 'js/gemini.js', 'js/restaurar.js']);
});

for (const bloque of deArchivo) {
  const ruta = bloque.code.split('\n')[0].slice(12).trim();
  test(`el bloque de ${ruta} es idéntico a solucion/${ruta}`, () => {
    const archivo = readFileSync(join(taller, 'solucion', ruta), 'utf8');
    assert.equal(archivo, bloque.code, `solucion/${ruta} y el codelab difieren`);
  });
}

test('cada bloque declara su lenguaje', () => {
  const sinLenguaje = [...md.matchAll(/^```\s*$/gm)].length;
  // Las vallas de cierre no llevan lenguaje: hay tantas como bloques.
  assert.equal(sinLenguaje, bloques.length);
});

test('las pruebas que pide correr el codelab existen en inicio/ y solucion/', () => {
  for (const b of bloques.filter((x) => x.lang === 'bash')) {
    for (const m of b.code.matchAll(/node --test (\S+)/g)) {
      assert.ok(existsSync(join(taller, 'inicio', m[1])), `inicio/${m[1]}`);
      assert.ok(existsSync(join(taller, 'solucion', m[1])), `solucion/${m[1]}`);
    }
  }
});

test('las imágenes del codelab existen en assets/', () => {
  for (const m of md.matchAll(/!\[[^\]]*\]\((assets\/[^)]+)\)/g)) {
    assert.ok(existsSync(join(taller, m[1])), m[1]);
  }
});
