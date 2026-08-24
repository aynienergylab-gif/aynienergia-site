const elevatedHeader = document.querySelector("[data-elevate]");
const menuToggle = document.querySelector(".menu-toggle");
const menu = document.querySelector("#menu");

const updateHeader = () => {
  elevatedHeader?.classList.toggle("is-scrolled", window.scrollY > 12);
};

const closeMenu = () => {
  document.body.classList.remove("menu-open");
  menu?.classList.remove("is-open");
  menuToggle?.setAttribute("aria-expanded", "false");
};

updateHeader();
window.addEventListener("scroll", updateHeader, { passive: true });

menuToggle?.addEventListener("click", () => {
  const willOpen = !menu?.classList.contains("is-open");
  document.body.classList.toggle("menu-open", willOpen);
  menu?.classList.toggle("is-open", willOpen);
  menuToggle.setAttribute("aria-expanded", String(willOpen));
});

menu?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", closeMenu);
});

const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        revealObserver.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.14 },
);

document.querySelectorAll(".reveal").forEach((element) => {
  revealObserver.observe(element);
});

const contactForm = document.querySelector(".contact-form");

contactForm?.addEventListener("submit", (event) => {
  event.preventDefault();

  const formData = new FormData(contactForm);
  const nome = String(formData.get("nome") || "").trim();
  const email = String(formData.get("email") || "").trim();
  const organizacao = String(formData.get("organizacao") || "").trim();
  const mensagem = String(formData.get("mensagem") || "").trim();

  const body = [
    `Nome: ${nome}`,
    `E-mail: ${email}`,
    `Organização: ${organizacao || "Não informada"}`,
    "",
    mensagem,
  ].join("\n");

  const subject = `Contato pelo site - ${nome || "sem nome"}`;
  window.location.href = `mailto:ayni.energy.lab@gmail.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
});
