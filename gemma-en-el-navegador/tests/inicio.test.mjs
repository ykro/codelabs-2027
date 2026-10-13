// inicio/ es solucion/ con los cinco archivos del alumno cambiados por un TODO.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const taller = join(dirname(fileURLToPath(import.meta.url)), '..');
const DEL_ALUMNO = ['js/modelo.js', 'js/anonimizador.js', 'js/detector.js', 'js/gemini.js', 'js/restaurar.js'];
const listar = (dir) => readdirSync(dir).flatMap((n) => (statSync(join(dir, n)).isDirectory() ? listar(join(dir, n)) : [join(dir, n)]));

test('inicio/ y solucion/ tienen los mismos archivos', () => {
  const a = listar(join(taller, 'inicio')).map((f) => relative(join(taller, 'inicio'), f)).sort();
  const b = listar(join(taller, 'solucion')).map((f) => relative(join(taller, 'solucion'), f)).sort();
  assert.deepEqual(a, b);
});

for (const archivo of listar(join(taller, 'solucion')).map((f) => relative(join(taller, 'solucion'), f))) {
  test(`inicio/${archivo}`, () => {
    const inicio = readFileSync(join(taller, 'inicio', archivo), 'utf8');
    const solucion = readFileSync(join(taller, 'solucion', archivo), 'utf8');
    if (DEL_ALUMNO.includes(archivo)) {
      assert.match(inicio, /TODO paso \d/);
      assert.equal(inicio.split('\n')[0], solucion.split('\n')[0]);
    } else {
      assert.equal(inicio, solucion);
    }
  });
}
