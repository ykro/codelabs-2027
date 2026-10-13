// archivo: js/detector.js
// La frontera de privacidad es código, no un prompt: revisa el texto que va a
// salir hacia la nube y devuelve cada dato personal que todavía encuentre.
import { contiene, nuevoMarcador, plano, reemplazar } from './texto.js';

// Formatos que se pueden verificar sin un modelo. El orden importa:
// un DPI se marca antes de que la regla de teléfono vea sus dígitos.
const PATRONES = [
  { tipo: 'CORREO', motivo: 'formato de correo', regex: /[\p{L}\p{N}._%+-]+@[\p{L}\p{N}-]+(?:\.[\p{L}\p{N}-]+)+/gu },
  { tipo: 'DPI', motivo: '13 dígitos seguidos', regex: /(?<!\d)\d{4}[ -]?\d{5}[ -]?\d{4}(?!\d)/g },
  { tipo: 'NIT', motivo: 'formato de NIT', regex: /(?<![\d-])\d{4,8}-[\dkK](?![\p{L}\p{N}])/gu },
  { tipo: 'TELEFONO', motivo: 'teléfono de 8 dígitos', regex: /(?<!\d)(?:\+?502[ -]?)?[2-7]\d{3}[ -]?\d{4}(?!\d)/g },
  { tipo: 'MONTO', motivo: 'monto en quetzales', regex: /(?<!\p{L})Q\.? ?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)? ?quetzales/giu },
  { tipo: 'DIRECCION', motivo: 'calle o avenida con número', regex: /(?:calle|avenida|av\.|calzada|diagonal) +\d{1,3}-\d{1,3}/giu },
  { tipo: 'NUMERO', motivo: 'número de 6 dígitos o más', regex: /\d{6,}/g },
  // Una palabra con mayúscula después de un título casi siempre es un nombre: «Dr. Ramírez», «don Julio».
  { tipo: 'NOMBRE', motivo: 'nombre después de un título', regex: /(?<=\b(?:[Dd]on|[Dd]oña|Dra?|Lic|Licda|Ing|Sra?|Srta)\.? )\p{Lu}\p{Ll}+/gu },
];
const TITULOS = new Set(['Don', 'Doña', 'Dr', 'Dra', 'Lic', 'Licda', 'Ing', 'Sr', 'Sra', 'Srta']);

// Palabras de un nombre que no identifican a nadie por sí solas.
const CONECTORES = new Set(['de', 'del', 'la', 'las', 'los', 'y', 'don', 'dona', 'dr', 'dra', 'sr', 'sra', 'lic', 'licda']);

// Dígito verificador del DPI (CUI) de Guatemala: 8 dígitos, verificador,
// departamento (01-22) y municipio.
const MUNICIPIOS = [17, 8, 16, 16, 13, 14, 19, 8, 24, 21, 9, 30, 32, 21, 8, 17, 14, 5, 11, 11, 7, 17];
export function dpiValido(valor) {
  const cui = valor.replace(/\D/g, '');
  if (cui.length !== 13) return false;
  const depto = Number(cui.slice(9, 11));
  const muni = Number(cui.slice(11, 13));
  if (depto < 1 || depto > 22 || muni < 1 || muni > MUNICIPIOS[depto - 1]) return false;
  const suma = [...cui.slice(0, 8)].reduce((total, d, i) => total + Number(d) * (i + 2), 0);
  return suma % 11 === Number(cui[8]);
}

export function buscarFugas(texto, mapa = {}) {
  const fugas = [];
  const vistos = new Set();
  const agregar = (fuga) => {
    const clave = plano(fuga.valor);
    if (vistos.has(clave)) return;
    vistos.add(clave);
    fugas.push(fuga);
  };

  // 1. Formatos conocidos. Lo que coincide se tapa para no contarlo dos veces.
  let resto = texto;
  for (const { tipo, motivo, regex } of PATRONES) {
    resto = resto.replace(regex, (valor) => {
      agregar({ tipo, valor, motivo: tipo === 'DPI' && dpiValido(valor) ? 'DPI con dígito verificador válido' : motivo });
      return '#'.repeat(valor.length);
    });
  }

  // 2. Valores originales del mapa que siguen en el texto.
  for (const [marcador, valor] of Object.entries(mapa)) {
    if (contiene(texto, valor)) agregar({ tipo: marcador.slice(1, marcador.lastIndexOf('_')), valor, marcador, motivo: `valor original de ${marcador}` });
  }

  // 3. Partes de un nombre conocido: «Carlos Xitumul» cuando el mapa tiene «Carlos Enrique Xitumul Coc».
  for (const [marcador, valor] of Object.entries(mapa)) {
    if (!marcador.startsWith('[NOMBRE_')) continue;
    for (const parte of valor.split(/[\s.,]+/)) {
      if (parte.length < 3 || CONECTORES.has(plano(parte))) continue;
      if (contiene(texto, parte)) agregar({ tipo: 'NOMBRE', valor: parte, motivo: `parte de ${marcador}` });
    }
  }

  return { ok: fugas.length === 0, fugas };
}

// Tapa lo que encontró el detector con marcadores nuevos (o el que ya tenía ese valor).
export function cubrirFugas(texto, mapa, fugas) {
  const nuevoMapa = { ...mapa };
  let nuevoTexto = texto;
  for (const fuga of fugas) {
    const marcador = fuga.marcador ?? nuevoMarcador(fuga.tipo, nuevoMapa);
    nuevoMapa[marcador] = fuga.valor;
    nuevoTexto = reemplazar(nuevoTexto, fuga.valor, marcador).split(fuga.valor).join(marcador);
  }
  return { texto: nuevoTexto, mapa: nuevoMapa };
}

// Lo que el código no puede saber: una palabra con mayúscula en medio de una
// oración puede ser un nombre que Gemma no vio. No bloquea; la persona decide.
export function revisarAMano(texto) {
  const palabras = [...texto.matchAll(/(?<=[\p{L}\p{N},;)\]] )\p{Lu}\p{Ll}+/gu)].map((m) => m[0]);
  return [...new Set(palabras.filter((p) => !TITULOS.has(p)))];
}
