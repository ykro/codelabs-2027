// Revisa el sitio generado en tamaños de teléfono y laptop:
// sin scroll horizontal de página, todos los pasos navegables y capturas para revisar.
//   node scripts/revisar_sitio.mjs [carpeta-capturas]
import { chromium } from 'playwright';
import { readdirSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

const dist = resolve('sitio/dist');
const salida = resolve(process.argv[2] || 'sitio/capturas');
mkdirSync(salida, { recursive: true });
const tamanos = [
  { nombre: 'telefono', width: 375, height: 812, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
  { nombre: 'laptop', width: 1280, height: 860, deviceScaleFactor: 1 },
];
const paginas = readdirSync(dist).filter((f) => f.endsWith('.html'));
const navegador = await chromium.launch();
let fallas = 0;
for (const t of tamanos) {
  const ctx = await navegador.newContext({ viewport: { width: t.width, height: t.height }, isMobile: t.isMobile, hasTouch: t.hasTouch, deviceScaleFactor: t.deviceScaleFactor });
  const page = await ctx.newPage();
  for (const p of paginas) {
    await page.goto(`file://${dist}/${p}`);
    const pasos = await page.locator('section.paso').count();
    for (let n = 1; n <= Math.max(pasos, 1); n++) {
      if (pasos) await page.goto(`file://${dist}/${p}#paso-${n}`);
      await page.waitForTimeout(50);
      const ancho = await page.evaluate(() => document.documentElement.scrollWidth);
      if (ancho > t.width + 1) {
        fallas++;
        const culpables = await page.evaluate((w) => [...document.querySelectorAll('body *')]
          .filter((e) => e.getBoundingClientRect().right > w + 1 && e.offsetParent !== null)
          .slice(0, 5).map((e) => `${e.tagName}.${e.className}`), t.width);
        console.log(`✗ ${t.nombre} ${p} paso ${n}: ancho ${ancho}px > ${t.width}px`, culpables.join(' | '));
      }
      await page.screenshot({ path: `${salida}/${p.replace('.html', '')}-${n}-${t.nombre}.png`, fullPage: true });
    }
  }
  await ctx.close();
}
await navegador.close();
console.log(fallas ? `${fallas} páginas con scroll horizontal` : 'Sin scroll horizontal en teléfono ni laptop');
process.exit(fallas ? 1 : 0);
