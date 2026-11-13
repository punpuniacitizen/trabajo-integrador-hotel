// Conserje: comportamiento común a todas las páginas.
(function () {
  // --- Menú lateral en pantallas chicas -----------------------------------
  const sidebar = document.getElementById("sidebar");
  const fondo = document.querySelector("[data-cerrar-menu]");

  function menu(abierto) {
    sidebar.classList.toggle("sidebar--abierta", abierto);
    fondo.hidden = !abierto;
  }

  document.querySelector("[data-abrir-menu]")?.addEventListener("click", () => menu(true));
  fondo?.addEventListener("click", () => menu(false));

  // --- Ctrl+K (o Cmd+K) enfoca el buscador ---------------------------------
  const buscador = document.getElementById("buscador");
  document.addEventListener("keydown", (evento) => {
    if ((evento.ctrlKey || evento.metaKey) && evento.key.toLowerCase() === "k") {
      evento.preventDefault();
      buscador?.focus();
      buscador?.select();
    }
  });

  // --- Avisos flotantes -----------------------------------------------------
  const contenedor = document.getElementById("toasts");

  // Los errores quedan más tiempo en pantalla
  function programarSalida(aviso) {
    const espera = aviso.classList.contains("toast--danger") ? 7000 : 4000;
    setTimeout(() => aviso.classList.add("toast--saliendo"), espera);
    setTimeout(() => aviso.remove(), espera + 300);
  }

  function toast(mensaje, tipo = "success") {
    const aviso = document.createElement("div");
    aviso.className = `toast toast--${tipo}`;
    aviso.textContent = mensaje;
    contenedor.appendChild(aviso);
    programarSalida(aviso);
  }

  // Los mensajes que manda el servidor (flash) ya vienen en el HTML
  contenedor.querySelectorAll(".toast").forEach(programarSalida);

  // --- POST con JSON a la API (ver app/routes/api.py) -----------------------
  async function postJSON(url, datos = {}) {
    const respuesta = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos),
    });
    // Sesión vencida: al recargar, el servidor manda al login
    if (respuesta.status === 401) {
      location.reload();
      return new Promise(() => {});
    }
    let cuerpo = {};
    try {
      cuerpo = await respuesta.json();
    } catch {
      // La respuesta no era JSON: se usa el mensaje genérico
    }
    if (!respuesta.ok || cuerpo.ok === false) {
      throw new Error(cuerpo.error || "No se pudo completar la acción.");
    }
    return cuerpo;
  }

  window.Conserje = { toast, postJSON };
})();
