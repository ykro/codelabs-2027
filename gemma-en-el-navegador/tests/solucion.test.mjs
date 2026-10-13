// Corre las pruebas de solucion/ (las mismas que el alumno corre con `node --test`).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const solucion = join(dirname(fileURLToPath(import.meta.url)), '..', 'solucion');

test('node --test pasa en solucion/', () => {
  const env = { ...process.env };
  delete env.NODE_TEST_CONTEXT; // si no, el proceso hijo le reporta al padre y no imprime nada
  const r = spawnSync(process.execPath, ['--test'], { cwd: solucion, encoding: 'utf8', env });
  assert.equal(r.status, 0, r.stdout + r.stderr);
  assert.match(r.stdout, /ℹ fail 0/);
});
