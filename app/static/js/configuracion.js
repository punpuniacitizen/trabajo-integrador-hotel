// Configuración: vistas previas de archivos, color de acento en vivo y ayudas de formularios.
(function () {
  // --- Vista previa al elegir un archivo (foto, logo, portada o modelo .glb) ----
  document.querySelectorAll("[data-subida]").forEach((subida) => {
    const input = subida.querySelector("input[data-preview]");
    const imagen = subida.querySelector(".subida__imagen");
    const modelo = subida.querySelector(".subida__modelo");
    const vacia = subida.querySelector(".subida__vacia");
    const nombre = subida.querySelector(".subida__nombre");
    const quitar = subida.querySelector('input[name^="quitar_"]');

    input.addEventListener("change", () => {
      const archivo = input.files[0];
      if (!archivo) return;
      const url = URL.createObjectURL(archivo);
      if (modelo) {
        modelo.src = url;
        modelo.hidden = false;
      } else {
        imagen.src = url;
        imagen.hidden = false;
      }
      vacia.hidden = true;
      nombre.textContent = `${archivo.name} · ${(archivo.size / 1024 / 1024).toFixed(1)} MB`;
      if (quitar) quitar.checked = false;
    });
  });

  // --- Color de acento: el hexadecimal y la muestra se actualizan al elegirlo ----
  const color = document.querySelector("[data-color-acento]");
  if (color) {
    const texto = document.querySelector("[data-color-texto]");
    const muestra = document.querySelector("[data-color-muestra]");
    const actualizar = () => {
      texto.textContent = color.value.toUpperCase();
      muestra.style.setProperty("--accent", color.value);
      muestra.style.setProperty("--accent-hover", color.value);
      // Mismo criterio que el servidor (app/services/tema.py): texto blanco o casi negro
      const [r, g, b] = [1, 3, 5].map((i) => {
        const c = parseInt(color.value.slice(i, i + 2), 16) / 255;
        return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
      });
      const luminancia = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      const conBlanco = 1.05 / (luminancia + 0.05);
      const conNegro = (luminancia + 0.05) / 0.0601;
      muestra.style.setProperty("--accent-contrast", conBlanco >= conNegro ? "#FFFFFF" : "#18181B");
    };
    color.addEventListener("input", actualizar);
    actualizar();
  }

  // --- Cambiar el tipo de una habitación con solo elegirlo --------------------
  document.querySelectorAll("[data-solo-sin-js]").forEach((boton) => (boton.hidden = true));
  document.querySelectorAll("select[data-autoenviar]").forEach((select) => {
    select.addEventListener("change", () => select.form.submit());
  });

  // --- "Nuevo piso": completa el número de piso siguiente --------------------
  document.querySelector("[data-nuevo-piso]")?.addEventListener("click", (evento) => {
    const form = evento.currentTarget.closest("form");
    form.elements.piso.value = evento.currentTarget.dataset.nuevoPiso;
    form.elements.desde.value = "";
    form.elements.cantidad.focus();
    form.elements.cantidad.select();
  });

  // --- Confirmación antes de borrar -------------------------------------------
  document.querySelectorAll("form[data-confirmar]").forEach((form) => {
    form.addEventListener("submit", (evento) => {
      if (!confirm(form.dataset.confirmar)) evento.preventDefault();
    });
  });
})();
