(() => {
  const pasos = [...document.querySelectorAll('.paso')];
  if (!pasos.length) return;
  const enlaces = [...document.querySelectorAll('.pasos a[data-paso]')];
  const menu = document.getElementById('menu-pasos');
  const actual = document.getElementById('paso-actual');
  const barra = document.getElementById('progreso');
  const portada = document.querySelector('.portada');
  const angosto = () => window.matchMedia('(max-width: 959px)').matches;
  document.body.classList.add('js');
  if (angosto()) menu.removeAttribute('open');

  function mostrar(n, desplazar) {
    n = Math.min(Math.max(n, 1), pasos.length);
    pasos.forEach((p, i) => p.classList.toggle('visible', i === n - 1));
    portada.classList.toggle('visible', n === 1);
    enlaces.forEach((a) => {
      const k = Number(a.dataset.paso);
      a.classList.toggle('activo', k === n);
      a.classList.toggle('hecho', k < n);
    });
    actual.textContent = `Paso ${n} de ${pasos.length}: ${pasos[n - 1].querySelector('h2').textContent}`;
    barra.style.width = `${(n / pasos.length) * 100}%`;
    if (angosto()) menu.removeAttribute('open');
    if (desplazar) window.scrollTo({ top: 0, behavior: 'instant' });
  }
  const desdeHash = () => Number((location.hash.match(/^#paso-(\d+)$/) || [])[1] || 1);
  window.addEventListener('hashchange', () => mostrar(desdeHash(), true));
  mostrar(desdeHash(), false);

  document.querySelectorAll('button.copiar').forEach((b) => {
    b.addEventListener('click', async () => {
      const texto = b.closest('figure').querySelector('pre').innerText;
      try {
        await navigator.clipboard.writeText(texto);
        b.textContent = 'Copiado';
      } catch {
        b.textContent = 'Selecciona y copia';
      }
      setTimeout(() => (b.textContent = 'Copiar'), 1600);
    });
  });
})();
