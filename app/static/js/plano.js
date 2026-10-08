// Plano de habitaciones: filtros, búsqueda, panel de detalle y acciones de recepción.
(function () {
  const plano = document.getElementById("plano");
  if (!plano) return;

  const panel = document.getElementById("plano-panel");
  const panelVacio = panel.innerHTML;
  const buscador = document.getElementById("buscador");
  const filtros = {
    piso: document.getElementById("filtro-piso"),
    tipo: document.getElementById("filtro-tipo"),
    estado: document.getElementById("filtro-estado"),
  };
  const fecha = plano.dataset.fecha;
  let seleccion = null; // número de la habitación abierta en el panel

  const tarjetas = () => plano.querySelectorAll(".habitacion");
  const conFecha = (url) => `${url}?fecha=${fecha}`;

  // --- Filtros y búsqueda -------------------------------------------------
  function aplicarFiltros() {
    const texto = buscador.value.trim().toLowerCase();
    let visibles = 0;
    tarjetas().forEach((tarjeta) => {
      const { piso, tipo, estado, busqueda } = tarjeta.dataset;
      const coincide =
        (!filtros.piso.value || piso === filtros.piso.value) &&
        (!filtros.tipo.value || tipo === filtros.tipo.value) &&
        (!filtros.estado.value || estado === filtros.estado.value) &&
        (!texto || busqueda.includes(texto));
      tarjeta.hidden = !coincide;
      if (coincide) visibles++;
    });
    plano.querySelectorAll(".piso").forEach((piso) => {
      piso.hidden = !piso.querySelector(".habitacion:not([hidden])");
    });
    document.getElementById("plano-sin-resultados").hidden = visibles > 0 || tarjetas().length === 0;
  }

  Object.values(filtros).forEach((select) => select.addEventListener("change", aplicarFiltros));
  buscador.addEventListener("input", aplicarFiltros);

  // --- Panel de detalle ---------------------------------------------------
  function marcarSeleccion() {
    tarjetas().forEach((t) => t.setAttribute("aria-pressed", String(t.dataset.numero === seleccion)));
  }

  async function abrir(numero) {
    const tarjeta = plano.querySelector(`.habitacion[data-numero="${CSS.escape(numero)}"]`);
    if (!tarjeta) return;
    seleccion = numero;
    marcarSeleccion();
    panel.classList.add("plano-panel--abierto");
    panel.setAttribute("aria-busy", "true");
    try {
      const respuesta = await fetch(conFecha(tarjeta.dataset.url));
      if (!respuesta.ok) throw new Error();
      panel.innerHTML = await respuesta.text();
      history.replaceState(null, "", `#hab-${numero}`);
    } catch {
      panel.innerHTML = panelVacio;
      Conserje.toast("No se pudo cargar la habitación.", "danger");
    } finally {
      panel.removeAttribute("aria-busy");
    }
  }

  function cerrar() {
    seleccion = null;
    marcarSeleccion();
    panel.classList.remove("plano-panel--abierto");
    panel.innerHTML = panelVacio;
    history.replaceState(null, "", location.pathname + location.search);
  }

  plano.addEventListener("click", (evento) => {
    const tarjeta = evento.target.closest(".habitacion");
    if (tarjeta) abrir(tarjeta.dataset.numero);
  });

  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape" && seleccion) cerrar();
  });

  // --- Acciones del panel -------------------------------------------------
  // Vuelve a pedir los indicadores y los pisos sin recargar la página.
  async function refrescar() {
    const respuesta = await fetch(conFecha(plano.dataset.urlContenido));
    const nuevo = new DOMParser().parseFromString(await respuesta.text(), "text/html");
    for (const id of ["plano-kpis", "plano-pisos"]) {
      document.getElementById(id).replaceWith(nuevo.getElementById(id));
    }
    aplicarFiltros();
    if (seleccion) await abrir(seleccion);
  }

  async function ejecutar(boton, url, datos) {
    boton.disabled = true;
    try {
      const { mensaje } = await Conserje.postJSON(url, datos);
      Conserje.toast(mensaje);
      await refrescar();
    } catch (error) {
      Conserje.toast(error.message, "danger");
      boton.disabled = false;
    }
  }

  panel.addEventListener("click", (evento) => {
    const objetivo = evento.target;
    const form = panel.querySelector(".panel__mantenimiento");

    if (objetivo.closest("[data-cerrar-panel]")) return cerrar();

    if (objetivo.closest("[data-mostrar-mantenimiento]")) {
      form.hidden = false;
      form.querySelector("input").focus();
      return;
    }
    if (objetivo.closest("[data-cancelar-mantenimiento]")) {
      form.hidden = true;
      return;
    }

    const boton = objetivo.closest("[data-accion]");
    if (!boton) return;
    if (boton.dataset.confirmar && !confirm(boton.dataset.confirmar)) return;
    ejecutar(boton, boton.dataset.accion, JSON.parse(boton.dataset.datos || "{}"));
  });

  panel.addEventListener("submit", (evento) => {
    const form = evento.target.closest(".panel__mantenimiento");
    if (!form) return;
    evento.preventDefault();
    ejecutar(form.querySelector("[type=submit]"), form.dataset.url, { activo: true, nota: form.nota.value });
  });

  // --- Selector de fecha --------------------------------------------------
  const inputFecha = document.getElementById("fecha-plano");
  document.querySelector("[data-abrir-calendario]").addEventListener("click", () => {
    try {
      inputFecha.showPicker();
    } catch {
      inputFecha.focus(); // navegadores sin showPicker()
    }
  });
  inputFecha.addEventListener("change", () => {
    if (inputFecha.value) location.href = `${location.pathname}?fecha=${inputFecha.value}`;
  });

  // Si la URL trae #hab-204, se abre esa habitación (sirve para compartir el link)
  const enlace = location.hash.match(/^#hab-(.+)$/);
  if (enlace) abrir(decodeURIComponent(enlace[1]));
})();
