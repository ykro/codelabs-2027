// Revisa el sitio publicado: estilos y JavaScript cargados, cada paso navegable y sin scroll horizontal en teléfono.
//   node scripts/revisar_publicado.mjs [https://codelabs-2027-z63pqhhmxq-uc.a.run.app]
import { chromium } from 'playwright';

const base = (process.argv[2] || 'https://codelabs-2027-z63pqhhmxq-uc.a.run.app').replace(/\/$/, '');
const paginas = ['', 'entrena-tu-david', 'agente-mcp', 'tienda-para-agentes', 'gemma-en-el-navegador'];
const navegador = await chromium.launch();
const ctx = await navegador.newContext({ viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true });
const page = await ctx.newPage();
const fallidos = [];
page.on('response', (r) => { if (r.status() >= 400) fallidos.push(`${r.status()} ${r.url()}`); });
let fallas = 0;
for (const p of paginas) {
  await page.goto(`${base}/${p}`, { waitUntil: 'networkidle' });
  const r = await page.evaluate(() => ({
    fondo: getComputedStyle(document.body).backgroundColor,
    js: document.body.classList.contains('js') || !document.querySelector('.paso'),
    pasos: document.querySelectorAll('.paso').length,
    visibles: [...document.querySelectorAll('.paso')].filter((s) => s.offsetParent !== null).length,
    ancho: document.documentElement.scrollWidth,
  }));
  const ok = r.fondo !== 'rgba(0, 0, 0, 0)' && r.js && r.ancho <= 376 && (r.pasos === 0 || r.visibles === 1);
  if (!ok) fallas++;
  console.log(`${ok ? '✓' : '✗'} /${p} · estilos ${r.fondo !== 'rgba(0, 0, 0, 0)' ? 'sí' : 'NO'} · js ${r.js ? 'sí' : 'NO'} · pasos ${r.pasos} (visibles ${r.visibles}) · ancho ${r.ancho}px`);
}
if (fallidos.length) { fallas++; console.log('Recursos con error:\n' + [...new Set(fallidos)].join('\n')); }
await navegador.close();
process.exit(fallas ? 1 : 0);
