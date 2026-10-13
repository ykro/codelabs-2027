// archivo: js/texto.js
// Utilidades de texto que usan el anonimizador, el detector y la restauración.

// Quita tildes y pasa a minúsculas sin cambiar la longitud del texto,
// así una posición en plano(texto) es la misma posición en texto.
export function plano(texto) {
  return texto.replace(/./gsu, (c) => {
    const base = c.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
    return base.length === c.length ? base : c;
  });
}

function escapar(valor) {
  return valor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Busca `valor` como palabra completa, sin importar tildes ni mayúsculas.
// «Ana» no coincide dentro de «Mariana».
export function posiciones(texto, valor) {
  const buscado = plano(valor.trim());
  if (!buscado) return [];
  const regex = new RegExp(`(?<![\\p{L}\\p{N}])${escapar(buscado)}(?![\\p{L}\\p{N}])`, 'gu');
  return [...plano(texto).matchAll(regex)].map((m) => [m.index, m.index + m[0].length]);
}

export function contiene(texto, valor) {
  return posiciones(texto, valor).length > 0;
}

// Reemplaza cada aparición de `valor` por `marcador`.
export function reemplazar(texto, valor, marcador) {
  let resultado = texto;
  for (const [inicio, fin] of posiciones(texto, valor).reverse()) {
    resultado = resultado.slice(0, inicio) + marcador + resultado.slice(fin);
  }
  return resultado;
}

// Siguiente marcador libre para un tipo: [NOMBRE_1], [NOMBRE_2], ...
export function nuevoMarcador(tipo, mapa) {
  let n = 1;
  while (`[${tipo}_${n}]` in mapa) n++;
  return `[${tipo}_${n}]`;
}
