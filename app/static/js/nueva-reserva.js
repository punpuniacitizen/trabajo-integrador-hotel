// Nueva reserva (administración): disponibilidad en vivo, buscador de huéspedes y resumen.
// El servidor vuelve a validar todo al guardar (app/services/reservas.py → crear_reserva).
(function () {
  const form = document.getElementById("nueva-reserva");
  if (!form) return;

  const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const DIA_MS = 86400000;
  const hoy = form.dataset.hoy;
  const { entrada, salida, personas, pagado } = form.elements;
  const huespedId = form.elements.huesped_id;

  // --- Fechas en formato ISO ("2026-10-14") -----------------------------------
  const aMs = (iso) => {
    const [anio, mes, dia] = iso.split("-").map(Number);
    return Date.UTC(anio, mes - 1, dia);
  };
  const sumarDias = (iso, dias) => new Date(aMs(iso) + dias * DIA_MS).toISOString().slice(0, 10);
  const fechaCorta = (iso) => {
    const fecha = new Date(aMs(iso));
    return `${fecha.getUTCDate()} ${MESES[fecha.getUTCMonth()]}`;
  };
  const rango = (desde, hasta) =>
    desde.slice(0, 7) === hasta.slice(0, 7)
      ? `${Number(desde.slice(8))} al ${fechaCorta(hasta)}`
      : `${fechaCorta(desde)} al ${fechaCorta(hasta)}`;
  const contarNoches = () =>
    entrada.value && salida.value ? Math.round((aMs(salida.value) - aMs(entrada.value)) / DIA_MS) : 0;

  const moneda = (valor) => `${form.dataset.moneda || "$"} ${valor.toLocaleString("es-AR")}`;
  const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;
  const iniciales = (nombre) =>
    nombre.split(/\s+/).filter((p) => /\p{L}/u.test(p[0] || "")).slice(0, 2).map((p) => p[0]).join("").toUpperCase() || "?";

  const elegida = () => form.querySelector('input[name="habitacion_id"]:checked');
  const campoResumen = (nombre) => form.querySelector(`[data-r-${nombre}]`);

  // Texto de un dato del resumen; si no hay valor, un "Sin…" atenuado
  function mostrar(nombre, texto, vacio) {
    const campo = campoResumen(nombre);
    campo.textContent = texto || vacio;
    campo.classList.toggle("muted", !texto);
  }

  function total() {
    const habitacion = elegida();
    const noches = contarNoches();
    return habitacion && noches > 0 ? Number(habitacion.dataset.tarifa) * noches : 0;
  }

  function nombreHuesped() {
    if (huespedId.value) return form.querySelector("[data-nombre]").textContent;
    return `${form.elements.nombre.value} ${form.elements.apellido.value}`.trim();
  }

  // --- Resumen en vivo ---------------------------------------------------------
  function actualizarResumen() {
    const habitacion = elegida();
    const noches = contarNoches();
    mostrar("habitacion", habitacion && `${habitacion.dataset.numero} · ${habitacion.dataset.tipo}`, "Sin elegir");
    mostrar("estadia", noches > 0 && `${rango(entrada.value, salida.value)} · ${plural(noches, "noche", "noches")}`, "—");
    mostrar("personas", personas.value, "—");
    mostrar("huesped", nombreHuesped(), "Sin cargar");

    const importe = total();
    const pago = Math.max(Number(pagado.value) || 0, 0);
    campoResumen("detalle").textContent =
      importe ? `${plural(noches, "noche", "noches")} × ${moneda(Number(habitacion.dataset.tarifa))}` : "";
    campoResumen("total").textContent = importe ? moneda(importe) : "—";
    campoResumen("pagado").textContent = moneda(pago);
    campoResumen("saldo").textContent = importe ? moneda(importe - pago) : "—";
    campoResumen("fila-saldo").classList.toggle("importes__saldo--pendiente", importe - pago > 0);

    // Marca el atajo de pago que coincide con lo cargado
    form.querySelectorAll("[data-pago]").forEach((boton) => {
      const coincide = Math.round((importe * Number(boton.dataset.pago)) / 100) === pago;
      boton.setAttribute("aria-pressed", String(coincide && (importe > 0 || pago === 0)));
    });

    // El check-in en el mismo paso solo tiene sentido si entra hoy
    const checkin = form.querySelector("[data-checkin]");
    checkin.hidden = entrada.value !== hoy;
    if (checkin.hidden) checkin.querySelector("input").checked = false;
  }

  // --- Atajos de pago: nada, la mitad o el total ---------------------------------
  form.querySelectorAll("[data-pago]").forEach((boton) => {
    boton.addEventListener("click", () => {
      const importe = total();
      if (!importe && boton.dataset.pago !== "0") {
        Conserje.toast("Elegí las fechas y la habitación para calcular el total.", "danger");
        return;
      }
      pagado.value = Math.round((importe * Number(boton.dataset.pago)) / 100);
      actualizarResumen();
    });
  });

  // --- Disponibilidad: al cambiar fechas o personas se vuelve a preguntar al servidor ---
  const tipos = form.querySelector(".nr-tipos");
  const aviso = form.querySelector("[data-aviso-habitacion]");
  const libres = form.querySelector("[data-libres]");
  let ultimoPedido = 0;

  function aplicarDisponibilidad(lista) {
    const porId = new Map(lista.map((h) => [String(h.id), h]));
    const anterior = elegida();
    let cantidad = 0;
    form.querySelectorAll('input[name="habitacion_id"]').forEach((input) => {
      const dato = porId.get(input.value);
      if (!dato) return;
      const libre = dato.estado === "libre";
      input.disabled = !libre;
      if (!libre) input.checked = false;
      const ficha = input.closest(".nr-hab");
      ficha.dataset.estado = dato.estado;
      ficha.querySelector("[data-motivo]").textContent = dato.motivo || "Libre";
      if (libre) cantidad += 1;
    });
    libres.textContent = cantidad;
    if (anterior && anterior.disabled) {
      aviso.textContent = `La ${anterior.dataset.numero} no está disponible con los datos nuevos. Elegí otra.`;
      aviso.hidden = false;
    }
    actualizarResumen();
  }

  async function consultarDisponibilidad() {
    if (contarNoches() <= 0) return;
    const pedido = ++ultimoPedido;
    tipos.classList.add("nr-tipos--cargando");
    const parametros = new URLSearchParams({ entrada: entrada.value, salida: salida.value, personas: personas.value });
    try {
      const respuesta = await fetch(`${form.dataset.urlDisponibilidad}?${parametros}`);
      if (respuesta.status === 401) {
        location.reload(); // sesión vencida: el servidor manda al login
        return;
      }
      const datos = await respuesta.json();
      if (pedido !== ultimoPedido) return; // ya se pidió otra cosa
      if (!datos.ok) throw new Error(datos.error);
      aplicarDisponibilidad(datos.habitaciones);
    } catch (error) {
      if (pedido === ultimoPedido) Conserje.toast(error.message || "No se pudo consultar la disponibilidad.", "danger");
    } finally {
      if (pedido === ultimoPedido) tipos.classList.remove("nr-tipos--cargando");
    }
  }

  // Si la salida queda antes de la entrada, se corre manteniendo la cantidad de noches
  let nochesPrevias = Math.max(contarNoches(), 1);
  entrada.addEventListener("change", () => {
    if (!entrada.value) return;
    salida.min = sumarDias(entrada.value, 1);
    if (!salida.value || salida.value <= entrada.value) salida.value = sumarDias(entrada.value, nochesPrevias);
  });

  form.addEventListener("change", (evento) => {
    const campo = evento.target.name;
    if (campo === "entrada" || campo === "salida" || campo === "personas") {
      if (contarNoches() > 0) nochesPrevias = contarNoches();
      consultarDisponibilidad();
    }
    if (campo === "habitacion_id") aviso.hidden = true;
    actualizarResumen();
  });
  form.addEventListener("input", actualizarResumen);

  // --- Huésped: buscar uno que ya vino o cargar uno nuevo ----------------------------
  const buscar = form.querySelector("[data-buscar-huesped]");
  const lista = document.getElementById("resultados-huesped");
  const bloqueBuscar = form.querySelector("[data-buscar]");
  const bloqueElegido = form.querySelector("[data-huesped-elegido]");
  const bloqueNuevo = form.querySelector("[data-huesped-nuevo]");
  let resultados = [];
  let activo = -1;
  let espera;

  const detalleHuesped = (h) =>
    [h.documento ? `Doc. ${h.documento}` : "Sin documento", h.email, h.pais].filter(Boolean).join(" · ");

  function cerrarLista() {
    lista.hidden = true;
    buscar.setAttribute("aria-expanded", "false");
    buscar.removeAttribute("aria-activedescendant");
  }

  function marcarActivo() {
    lista.querySelectorAll(".nr-resultado").forEach((item, i) => {
      item.setAttribute("aria-selected", String(i === activo));
      if (i === activo) {
        item.scrollIntoView({ block: "nearest" });
        buscar.setAttribute("aria-activedescendant", item.id);
      }
    });
  }

  function mostrarResultados() {
    lista.replaceChildren();
    if (!resultados.length) {
      const vacio = document.createElement("li");
      vacio.className = "nr-resultados__vacio";
      vacio.textContent = "No encontramos a nadie así. Cargalo abajo como huésped nuevo.";
      lista.append(vacio);
    }
    resultados.forEach((h) => {
      const item = document.createElement("li");
      item.className = "nr-resultado";
      item.id = `huesped-${h.id}`;
      item.setAttribute("role", "option");

      const avatar = document.createElement("span");
      avatar.className = "avatar avatar--sm";
      avatar.textContent = iniciales(h.nombre);
      const texto = document.createElement("div");
      const nombre = document.createElement("strong");
      nombre.textContent = h.nombre;
      const detalle = document.createElement("p");
      detalle.textContent = detalleHuesped(h);
      texto.append(nombre, detalle);
      const estadias = document.createElement("span");
      estadias.className = "nr-resultado__estadias";
      estadias.textContent = h.estadias ? plural(h.estadias, "estadía", "estadías") : "Sin estadías";
      item.append(avatar, texto, estadias);

      // mousedown (y no click) para elegir antes de que el buscador pierda el foco
      item.addEventListener("mousedown", (evento) => {
        evento.preventDefault();
        elegir(h);
      });
      lista.append(item);
    });
    lista.hidden = false;
    buscar.setAttribute("aria-expanded", "true");
    marcarActivo();
  }

  function elegir(h) {
    huespedId.value = h.id;
    bloqueElegido.querySelector("[data-avatar]").textContent = iniciales(h.nombre);
    bloqueElegido.querySelector("[data-nombre]").textContent = h.nombre;
    bloqueElegido.querySelector("[data-detalle]").textContent = detalleHuesped(h);
    bloqueElegido.hidden = false;
    bloqueBuscar.hidden = true;
    // Deshabilitado, el formulario de huésped nuevo no se manda ni pide sus campos obligatorios
    bloqueNuevo.hidden = bloqueNuevo.disabled = true;
    buscar.value = "";
    cerrarLista();
    actualizarResumen();
  }

  form.querySelector("[data-cambiar-huesped]").addEventListener("click", () => {
    huespedId.value = "";
    bloqueElegido.hidden = true;
    bloqueBuscar.hidden = false;
    bloqueNuevo.hidden = bloqueNuevo.disabled = false;
    buscar.focus();
    actualizarResumen();
  });

  buscar.addEventListener("input", () => {
    clearTimeout(espera);
    const texto = buscar.value.trim();
    if (texto.length < 2) {
      cerrarLista();
      return;
    }
    espera = setTimeout(async () => {
      try {
        const respuesta = await fetch(`${form.dataset.urlHuespedes}?${new URLSearchParams({ q: texto })}`);
        if (respuesta.status === 401) {
          location.reload();
          return;
        }
        const datos = await respuesta.json();
        if (buscar.value.trim() !== texto) return; // ya escribió otra cosa
        resultados = datos.huespedes || [];
        activo = resultados.length ? 0 : -1;
        mostrarResultados();
      } catch {
        Conserje.toast("No se pudo buscar huéspedes.", "danger");
      }
    }, 200);
  });

  buscar.addEventListener("keydown", (evento) => {
    // Enter elige el resultado marcado (y no manda el formulario)
    if (evento.key === "Enter") {
      evento.preventDefault();
      if (!lista.hidden && resultados[activo]) elegir(resultados[activo]);
      return;
    }
    if (evento.key === "Escape") {
      cerrarLista();
      return;
    }
    if (lista.hidden || !resultados.length) return;
    if (evento.key === "ArrowDown" || evento.key === "ArrowUp") {
      evento.preventDefault();
      const paso = evento.key === "ArrowDown" ? 1 : -1;
      activo = (activo + paso + resultados.length) % resultados.length;
      marcarActivo();
    }
  });

  buscar.addEventListener("blur", cerrarLista);

  actualizarResumen();
})();
