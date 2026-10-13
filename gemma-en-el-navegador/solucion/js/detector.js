// archivo: js/detector.js
// La frontera de privacidad es código, no un prompt: revisa el texto que va a
// salir hacia la nube y devuelve cada dato personal que todavía encuentre.
import { formas, nuevoMarcador, plano, reemplazarExacto } from './texto.js';

// Títulos y parentescos: la palabra con mayúscula que sigue casi siempre es un nombre.
const TITULOS = ['don', 'doña', 'dr', 'dra', 'lic', 'licda', 'ing', 'sr', 'sra', 'srta', 'doctor', 'doctora',
  'licenciado', 'licenciada', 'ingeniero', 'ingeniera', 'señor', 'señora', 'señorita', 'seño', 'profe',
  'profesor', 'profesora', 'tío', 'tía', 'hermano', 'hermana', 'esposo', 'esposa', 'hijo', 'hija', 'primo',
  'prima', 'abuelo', 'abuela', 'cuñado', 'cuñada', 'compadre', 'comadre'];
const ANTES_DE_NOMBRE = `(?<![\\p{L}])(?:${TITULOS.map((t) => `[${t[0].toUpperCase()}${t[0]}]${t.slice(1)}`).join('|')})\\.? `;

// Formatos que se pueden verificar sin un modelo. El orden importa:
// lo que una regla encuentra se tapa antes de que la siguiente lo vea.
const PATRONES = [
  { tipo: 'CORREO', motivo: 'formato de correo', regex: /[\p{L}\p{N}._%+-]+@[\p{L}\p{N}-]+(?:\.[\p{L}\p{N}-]+)+/gu },
  { tipo: 'USUARIO', motivo: 'usuario de red social', regex: /(?<![\p{L}\p{N}.])@[\p{L}\p{N}._]{2,}[\p{L}\p{N}_]/gu },
  { tipo: 'TARJETA', motivo: '16 dígitos de tarjeta', regex: /(?<!\d)\d{4}(?:[ -]?\d{4}){3}(?!\d)/g },
  { tipo: 'DPI', motivo: '13 dígitos seguidos', regex: /(?<!\d)\d{4}[ .-]?\d{5}[ .-]?\d{4}(?!\d)/g },
  { tipo: 'TELEFONO', motivo: 'teléfono de 8 dígitos', regex: /(?<!\d)(?:\+?502[ .-]?)?(?:[2-7]\d{3}[ .-]?\d{4}|[2-7]\d(?:[ .-]\d{2}){3})(?!\d)/g },
  { tipo: 'TELEFONO', motivo: 'teléfono internacional', regex: /\+\d{1,3}[ .-]?\(?\d{1,4}\)?(?:[ .-]?\d){6,}/g },
  { tipo: 'FECHA', motivo: 'fecha con año', regex: /(?<!\d)\d{1,2}[/.-]\d{1,2}[/.-](?:\d{4}|\d{2})(?!\d)/g },
  { tipo: 'PLACA', motivo: 'placa de Guatemala', regex: /(?<![\p{L}\p{N}])(?:P|M|C|A|O|U|TC|CD|MI)[ -]?\d{3}[A-Z]{3}(?![\p{L}\p{N}])/giu },
  { tipo: 'NIT', motivo: 'formato de NIT', regex: /(?<![\d-])\d{4,8}-[\dkK](?![\p{L}\p{N}])/gu },
  { tipo: 'MONTO', motivo: 'monto en quetzales', regex: /(?<!\p{L})Q\.? ?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)? ?quetzales/giu },
  { tipo: 'DIRECCION', motivo: 'calle o avenida con número', regex: /(?:calle|avenida|av\.|calzada|diagonal) +\d{1,3}-\d{1,3}/giu },
  { tipo: 'DIRECCION', motivo: 'lote, casa o manzana', regex: /(?<!\p{L})(?:[Ll]ote|[Cc]asa|[Mm]anzana|[Aa]partamento|[Aa]pto\.?) +(?:\d+|\p{Lu})(?![\p{L}\p{N}])/gu },
  { tipo: 'NUMERO', motivo: 'número de 6 dígitos o más', regex: /\d{6,}/g },
  { tipo: 'NUMERO', motivo: 'número con guiones (cuenta, póliza)', regex: /(?<![\d-])\d{2,}-\d{2,}-\d+(?![\d-])/g },
  { tipo: 'NOMBRE', motivo: 'nombre después de un título o parentesco', regex: new RegExp(`(?<=${ANTES_DE_NOMBRE})\\p{Lu}\\p{Ll}+`, 'gu') },
];

// Palabras de un nombre que no identifican a nadie por sí solas.
const CONECTORES = new Set(['de', 'del', 'la', 'las', 'los', 'y', ...TITULOS.map(plano)]);

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
  // Cada fuga guarda el valor tal como está escrito en el texto, para restaurarlo igual.
  const agregar = (fuga) => {
    if (vistos.has(fuga.valor)) return;
    vistos.add(fuga.valor);
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

  // 2. Valores originales del mapa que siguen en el texto, sin importar tildes ni mayúsculas.
  for (const [marcador, valor] of Object.entries(mapa)) {
    for (const forma of formas(texto, valor)) {
      agregar({ tipo: marcador.slice(1, marcador.lastIndexOf('_')), valor: forma, marcador, motivo: `valor original de ${marcador}` });
    }
  }

  // 3. Partes de un nombre conocido: «Carlos Xitumul» cuando el mapa tiene «Carlos Enrique Xitumul Coc».
  for (const [marcador, valor] of Object.entries(mapa)) {
    if (!marcador.startsWith('[NOMBRE_')) continue;
    for (const parte of valor.split(/[\s.,]+/)) {
      if (parte.length < 3 || CONECTORES.has(plano(parte))) continue;
      for (const forma of formas(texto, parte)) agregar({ tipo: 'NOMBRE', valor: forma, motivo: `parte de ${marcador}` });
    }
  }

  return { ok: fugas.length === 0, fugas };
}

// Tapa lo que encontró el detector. Reusa el marcador si el valor es idéntico al del mapa;
// si no, crea uno nuevo, así la restauración devuelve el texto tal como estaba.
export function cubrirFugas(texto, mapa, fugas) {
  const nuevoMapa = { ...mapa };
  let nuevoTexto = texto;
  for (const fuga of fugas) {
    const marcador = fuga.marcador && mapa[fuga.marcador] === fuga.valor ? fuga.marcador : nuevoMarcador(fuga.tipo, nuevoMapa);
    nuevoMapa[marcador] = fuga.valor;
    nuevoTexto = reemplazarExacto(nuevoTexto, fuga.valor, marcador).split(fuga.valor).join(marcador);
  }
  return { texto: nuevoTexto, mapa: nuevoMapa };
}

// Lo que el código no puede saber, pero puede señalar para que la persona lo revise.
// No bloquea por sí solo: obliga a confirmar antes de enviar.
const COMUNES = new Set(['de', 'del', 'la', 'el', 'los', 'las', 'que', 'y', 'es', 'se', 'me', 'no', 'en', 'a', 'con',
  'por', 'para', 'lo', 'le', 'les', 'su', 'sus', 'mi', 'mis', 'ya', 'un', 'una', 'al', 'nos', 'muy']);
export function revisarAMano(texto) {
  const palabras = [
    // Mayúscula en medio de una oración: «mi hija Sofía», «calzada Roosevelt».
    ...[...texto.matchAll(/(?<=[\p{L}\p{N},;:)\]] )\p{Lu}\p{Ll}+/gu)].map((m) => m[0]),
    // Minúscula después de un título o parentesco: «mi tío beto».
    ...[...texto.matchAll(new RegExp(`(?<=${ANTES_DE_NOMBRE})\\p{Ll}+`, 'gu'))].map((m) => m[0]),
    // Después de «soy», «me llamo» o «mi nombre es»: «soy ana».
    ...[...texto.matchAll(/(?<=(?<![\p{L}])(?:[Ss]oy|[Mm]e llamo|[Mm]i nombre es) )\p{L}+/gu)].map((m) => m[0]),
  ];
  const titulos = new Set(TITULOS.map(plano));
  return [...new Set(palabras.filter((p) => !titulos.has(plano(p)) && !COMUNES.has(plano(p))))];
}

// Un texto puede traer instrucciones para el modelo («responde {"datos":[]}»).
// Gemma puede obedecerlas. Esta lista solo reconoce frases conocidas: una instrucción
// redactada de otra forma pasa sin aviso. Por eso la página siempre pide confirmar.
export function pareceInyeccion(texto) {
  return /ignora|instrucci[oó]n|responde (?:exactamente|solo|únicamente)|\{\s*"datos"|system prompt|asistente|modelo de lenguaje|anonimiz|lista(?:r)? solo|no (?:listes|incluyas|cuentan como datos)|no (?:son|contiene) datos personales|personajes? p[uú]blicos?/iu.test(texto);
}
