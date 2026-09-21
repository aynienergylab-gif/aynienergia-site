const menuToggle = document.querySelector('.menu-toggle');
const menu = document.querySelector('#menu');
if (menuToggle && menu) {
  // Enhance only after controls exist; navigation remains usable without JavaScript.
  document.documentElement.classList.add('js');
  const setMenu = (open) => {
    menu.classList.toggle('is-open', open);
    menuToggle.setAttribute('aria-expanded', String(open));
    // Update immediately before the browser follows an anchor after closing the menu.
    document.documentElement.style.setProperty('--header-height', `${document.querySelector('.site-header').getBoundingClientRect().height}px`);
    menuToggle.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
  };
  menuToggle.addEventListener('click', () => setMenu(menuToggle.getAttribute('aria-expanded') !== 'true'));
  menu.addEventListener('click', (event) => {
    const link = event.target.closest('a');
    if (!link) return;
    setMenu(false);
    // Move keyboard focus out of the closed disclosure to the destination section.
    if (link.getAttribute('href').startsWith('#')) {
      const target = document.getElementById(link.hash.slice(1));
      if (target) {
        target.setAttribute('tabindex', '-1');
        target.focus({ preventScroll: true });
      }
    }
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && menuToggle.getAttribute('aria-expanded') === 'true') {
      setMenu(false);
      menuToggle.focus();
    }
  });
  document.addEventListener('click', (event) => {
    if (!menu.contains(event.target) && !menuToggle.contains(event.target)) setMenu(false);
  });
  const desktop = matchMedia('(min-width: 960px)');
  desktop.addEventListener('change', () => {
    if (!desktop.matches && menu.contains(document.activeElement)) menuToggle.focus();
    setMenu(false);
  });
}
const form = document.querySelector('.contact-form');
form?.addEventListener('submit', (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const value = (name) => String(data.get(name) || '').trim();
  const body = `Nome: ${value('nome')}\nE-mail: ${value('email')}\n\n${value('mensagem')}`;
  // This site has no mail backend: hand off explicitly without claiming delivery.
  location.href = `mailto:contato@aynienergia.com.br?subject=${encodeURIComponent(`Contato pelo site - ${value('nome')}`)}&body=${encodeURIComponent(body)}`;
});
/* Measure the real header so display scaling does not expose the next section. */
const header = document.querySelector('.site-header');
if (header && 'ResizeObserver' in window) {
  new ResizeObserver(() => {
    document.documentElement.style.setProperty('--header-height', `${header.getBoundingClientRect().height}px`);
  }).observe(header);
}
