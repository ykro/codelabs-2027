// La versión «app de una sola página» de la tienda: el servidor manda un HTML
// vacío y este script dibuja todo en el navegador. Las personas la ven bien;
// un agente que lee el HTML no ve nada.
const q = (c) => `Q${(c / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
const esc = (s) => String(s).replace(/[&<>"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);

const cabecera = `<header class="cabecera"><a class="marca" href="/"><span class="cometa" aria-hidden="true"></span>Tostaduría Barrilete</a>
  <nav><a href="/">Café</a><a href="/envios">Envíos</a></nav></header>`;

function inicio(productos) {
  const tarjetas = productos.map((p) => `
    <a class="tarjeta" href="/cafe/${p.slug}">
      <img src="/static/img/${p.slug}.jpg" alt="Bolsa de café ${esc(p.nombre)}" width="320" height="320">
      <div class="tarjeta-texto"><p class="region">${esc(p.region)} · ${esc(p.altura)}</p><h2>${esc(p.nombre)}</h2>
      <p class="notas">${esc(p.notas)}</p><p class="precio">Desde ${q(Math.min(...p.variantes.map((v) => v.precio)))}</p></div>
    </a>`).join('');
  return `<section class="portada"><h1>Café de altura, tostado cada semana</h1>
    <p>Café de altura de Guatemala, tostado cada semana en Ciudad de Guatemala. Envío a toda Guatemala.</p></section>
    <section class="rejilla">${tarjetas}</section>`;
}

function ficha(p) {
  const filas = p.variantes.map((v) => `<li class="${v.disponible ? '' : 'agotada'}"><span>${esc(v.presentacion)}</span>
    <span class="precio">${q(v.precio)}</span><span class="estado">${v.disponible ? 'Disponible' : 'Agotado'}</span></li>`).join('');
  const opciones = p.variantes.filter((v) => v.disponible)
    .map((v) => `<option value="${v.sku}">${esc(v.presentacion)} · ${q(v.precio)}</option>`).join('');
  document.title = `${p.nombre} · Tostaduría Barrilete`;
  return `<article class="ficha"><img class="ficha-foto" src="/static/img/${p.slug}.jpg" alt="Bolsa de café ${esc(p.nombre)}" width="480" height="480">
    <div><p class="region">${esc(p.region)} · ${esc(p.altura)} · proceso ${esc(p.proceso.toLowerCase())} · tueste ${esc(p.tueste.toLowerCase())}</p>
    <h1>${esc(p.nombre)}</h1><p class="notas">${esc(p.notas)}</p><h2>Presentaciones</h2><ul class="variantes">${filas}</ul>
    <form class="pedir" method="post" action="/pedidos"><label>Presentación <select name="sku">${opciones}</select></label>
    <label>Cantidad <input name="cantidad" type="number" min="1" max="10" value="1"></label>
    <label>Tu nombre <input name="nombre" autocomplete="name" required></label><button type="submit">Pedir</button></form>
    <p class="envio">Envío estándar Q20.00: llega en 2 a 3 días hábiles. <a href="/envios">Ver envíos</a></p></div></article>`;
}

fetch('/api/productos').then((r) => r.json()).then((productos) => {
  const slug = location.pathname.startsWith('/cafe/') ? location.pathname.split('/')[2] : null;
  const p = slug && productos.find((x) => x.slug === slug);
  const cuerpo = slug ? (p ? ficha(p) : '<p class="texto">Producto no encontrado.</p>') : inicio(productos);
  document.getElementById('app').innerHTML = `${cabecera}<main>${cuerpo}</main>
    <footer class="pie">Tienda ficticia para el codelab «Haz tu tienda legible para agentes». Precios en quetzales.</footer>`;
});
