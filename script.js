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
  menuToggle?.setAttribute("aria-label", "Abrir menu");
};

updateHeader();
window.addEventListener("scroll", updateHeader, { passive: true });

menuToggle?.addEventListener("click", () => {
  const willOpen = !menu?.classList.contains("is-open");
  document.body.classList.toggle("menu-open", willOpen);
  menu?.classList.toggle("is-open", willOpen);
  menuToggle.setAttribute("aria-expanded", String(willOpen));
  menuToggle.setAttribute("aria-label", willOpen ? "Fechar menu" : "Abrir menu");
});

menu?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", closeMenu);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && menu?.classList.contains("is-open")) {
    closeMenu();
    menuToggle?.focus();
  }
});

const revealElements = document.querySelectorAll(".reveal");

if ("IntersectionObserver" in window && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
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

  revealElements.forEach((element) => revealObserver.observe(element));
} else {
  revealElements.forEach((element) => element.classList.add("is-visible"));
}

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
