// Menu em disclosure abaixo de 1024px; sem JavaScript a navegação fica sempre visível.
const menuToggle = document.querySelector('.menu-toggle');
if (menuToggle) {
  const setMenu = (open) => {
    menuToggle.setAttribute('aria-expanded', String(open));
    menuToggle.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
  };
  const isOpen = () => menuToggle.getAttribute('aria-expanded') === 'true';
  menuToggle.addEventListener('click', () => setMenu(!isOpen()));
  document.getElementById('menu').addEventListener('click', (event) => {
    if (event.target.closest('a')) setMenu(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && isOpen()) {
      setMenu(false);
      menuToggle.focus();
    }
  });
  matchMedia('(min-width: 1024px)').addEventListener('change', () => setMenu(false));
}

// Pílulas de categoria (producao.html): marca a âncora atual.
const pills = [...document.querySelectorAll('.pilula')];
if (pills.length) {
  const syncPills = () => {
    const current = pills.find((pill) => pill.hash === location.hash) || pills[0];
    pills.forEach((pill) => {
      if (pill === current) pill.setAttribute('aria-current', 'true');
      else pill.removeAttribute('aria-current');
    });
  };
  addEventListener('hashchange', syncPills);
  syncPills();
}
