// archivo: js/restaurar.js
// La respuesta de la nube vuelve con marcadores; aquí, en tu dispositivo,
// se cambian por los datos reales. Gemini nunca los vio.
export function restaurar(texto, mapa) {
  let resultado = texto;
  for (const [marcador, valor] of Object.entries(mapa)) {
    resultado = resultado.split(marcador).join(valor);
  }
  // Marcadores que Gemini inventó o cambió: se dejan visibles para que la persona los revise.
  const sinRestaurar = [...new Set(resultado.match(/\[[A-Z]+_\d+\]/g) ?? [])];
  return { texto: resultado, sinRestaurar };
}
