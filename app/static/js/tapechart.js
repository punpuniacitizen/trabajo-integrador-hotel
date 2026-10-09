// Tape chart: arrastrar reservas para cambiarlas de habitación o de fechas, y estirarlas.
// El servidor vuelve a validar todo (app/services/reservas.py); acá se valida lo que se ve
// en pantalla para dar una respuesta inmediata en el tooltip.
(function () {
  const scroll = document.getElementById("tape-scroll");
  if (!scroll) return;

  const tooltip = document.getElementById("tape-tooltip");
  const buscador = document.getElementById("buscador");
  const hoy = scroll.dataset.hoy;
  const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const DIA_MS = 86400000;
  const UMBRAL_PX = 4; // menos que esto es un clic, no un arrastre

  // --- Fechas en formato ISO ("2026-10-14"); se comparan como texto -------
  const aMs = (iso) => {
    const [anio, mes, dia] = iso.split("-").map(Number);
    return Date.UTC(anio, mes - 1, dia);
  };
  const aIso = (ms) => new Date(ms).toISOString().slice(0, 10);
  const sumarDias = (iso, dias) => aIso(aMs(iso) + dias * DIA_MS);
  const contarNoches = (entrada, salida) => Math.round((aMs(salida) - aMs(entrada)) / DIA_MS);
  const fechaCorta = (iso) => {
    const fecha = new Date(aMs(iso));
    return `${fecha.getUTCDate()} ${MESES[fecha.getUTCMonth()]}`;
  };
  const rango = (entrada, salida) =>
    entrada.slice(0, 7) === salida.slice(0, 7)
      ? `${Number(entrada.slice(8))} al ${fechaCorta(salida)}`
      : `${fechaCorta(entrada)} al ${fechaCorta(salida)}`;

  let arrastre = null;

  const anchoDia = () => scroll.querySelector(".tape__dia").getBoundingClientRect().width;
  const filaBajo = (x, y) => document.elementsFromPoint(x, y).find((el) => el.classList.contains("tape__fila"));

  // Por qué no se puede soltar ahí (o null si está disponible)
  function motivoDeRechazo(a) {
    const { barra, fila, entrada, salida } = a;
    const numero = fila.dataset.numero;
    if (fila.dataset.bloqueada) return `La ${numero} está en mantenimiento`;
    const capacidad = Number(fila.dataset.capacidad);
    if (Number(barra.dataset.personas) > capacidad) {
      return `La ${numero} es para ${capacidad} ${capacidad === 1 ? "persona" : "personas"}`;
    }
    if (barra.dataset.mover === "todo" && entrada < hoy) return "La entrada no puede quedar en el pasado";
    if (salida < hoy) return "La salida no puede quedar en el pasado";
    const pisa = [...fila.querySelectorAll(".barra-reserva[data-id]")].some(
      (otra) => otra !== barra && otra.dataset.entrada < salida && otra.dataset.salida > entrada
    );
    if (pisa) return `La ${numero} está ocupada esas noches`;
    return null;
  }

  function marcarDestino(fila) {
    scroll.querySelectorAll(".tape__fila--destino").forEach((f) => f.classList.remove("tape__fila--destino"));
    fila?.classList.add("tape__fila--destino");
  }

  function mostrarTooltip(a) {
    const noches = contarNoches(a.entrada, a.salida);
    const accion = a.estirar
      ? `Salida el ${fechaCorta(a.salida)}`
      : `Mover a ${a.fila.dataset.numero} · ${rango(a.entrada, a.salida)}`;
    const texto = document.createElement("span");
    texto.textContent = `${accion} (${noches} ${noches === 1 ? "noche" : "noches"})`;
    const estado = document.createElement("span");
    estado.className = "tape-tooltip__estado";
    estado.textContent = a.motivo ? "No disponible" : "Disponible";
    tooltip.replaceChildren(texto, estado);
    tooltip.classList.toggle("tape-tooltip--error", Boolean(a.motivo));

    const caja = a.barra.getBoundingClientRect();
    tooltip.style.left = `${caja.left + caja.width / 2}px`;
    tooltip.style.top = `${caja.top}px`;
    tooltip.hidden = false;
  }

  // Si se arrastra cerca del borde de la grilla, la grilla se desplaza sola
  function autoDesplazar(evento) {
    const MARGEN = 40;
    const PASO = 12;
    const caja = scroll.getBoundingClientRect();
    if (evento.clientY > caja.bottom - MARGEN) scroll.scrollTop += PASO;
    else if (evento.clientY < caja.top + MARGEN + 52) scroll.scrollTop -= PASO; // 52 = encabezado de días
  }

  function restaurar(a) {
    a.barra.classList.remove("barra-reserva--arrastrando");
    a.barra.style.transform = "";
    a.barra.style.marginRight = "";
    tooltip.hidden = true;
    marcarDestino(null);
  }

  // --- Arrastre con pointer events (sirve para mouse y pantallas táctiles) ---
  scroll.addEventListener("pointerdown", (evento) => {
    const barra = evento.target.closest(".barra-reserva[data-id]");
    if (!barra || evento.button !== 0) return;
    const fila = barra.closest(".tape__fila");
    arrastre = {
      barra,
      fila,
      filaOrigen: fila,
      estirar: Boolean(evento.target.closest(".barra-reserva__estirar")),
      x0: evento.clientX,
      y0: evento.clientY,
      ancho: anchoDia(),
      entrada: barra.dataset.entrada,
      salida: barra.dataset.salida,
      movido: false,
      motivo: null,
    };
    barra.setPointerCapture(evento.pointerId);
  });

  scroll.addEventListener("pointermove", (evento) => {
    const a = arrastre;
    if (!a) return;
    const dx = evento.clientX - a.x0;
    const dy = evento.clientY - a.y0;
    if (!a.movido) {
      if (Math.hypot(dx, dy) < UMBRAL_PX || !a.barra.dataset.mover) return;
      a.movido = true;
      a.barra.classList.add("barra-reserva--arrastrando");
    }

    autoDesplazar(evento);
    const { barra } = a;
    const dias = Math.round(dx / a.ancho);
    if (a.estirar) {
      // Al menos una noche
      const minimo = 1 - contarNoches(barra.dataset.entrada, barra.dataset.salida);
      const delta = Math.max(dias, minimo);
      a.salida = sumarDias(barra.dataset.salida, delta);
      barra.style.marginRight = `${2 - delta * a.ancho}px`;
    } else {
      // Un huésped alojado solo puede cambiar de habitación, no de fechas
      const delta = barra.dataset.mover === "todo" ? dias : 0;
      a.fila = filaBajo(evento.clientX, evento.clientY) || a.fila;
      a.entrada = sumarDias(barra.dataset.entrada, delta);
      a.salida = sumarDias(barra.dataset.salida, delta);
      const despY = a.fila.getBoundingClientRect().top - a.filaOrigen.getBoundingClientRect().top;
      barra.style.transform = `translate(${delta * a.ancho}px, ${despY}px)`;
    }
    a.motivo = motivoDeRechazo(a);
    marcarDestino(a.fila);
    mostrarTooltip(a);
  });

  scroll.addEventListener("pointerup", async () => {
    const a = arrastre;
    if (!a) return;
    arrastre = null;

    if (!a.movido) {
      location.href = a.barra.dataset.detalle; // clic: ver la reserva en el plano
      return;
    }
    const sinCambios =
      a.fila === a.filaOrigen && a.entrada === a.barra.dataset.entrada && a.salida === a.barra.dataset.salida;
    if (sinCambios) return restaurar(a);
    if (a.motivo) {
      Conserje.toast(`${a.motivo}.`, "danger");
      return restaurar(a);
    }

    tooltip.hidden = true;
    try {
      const url = scroll.dataset.urlMover.replace("/0/", `/${a.barra.dataset.id}/`);
      const { mensaje } = await Conserje.postJSON(url, {
        habitacion_id: Number(a.fila.dataset.habitacion),
        entrada: a.entrada,
        salida: a.salida,
      });
      Conserje.toast(mensaje);
      await refrescar();
    } catch (error) {
      Conserje.toast(error.message, "danger");
      restaurar(a);
    }
  });

  scroll.addEventListener("pointercancel", () => {
    if (arrastre) restaurar(arrastre);
    arrastre = null;
  });

  // Enter sobre una reserva abre su detalle
  scroll.addEventListener("keydown", (evento) => {
    const barra = evento.target.closest(".barra-reserva[data-id]");
    if (barra && evento.key === "Enter") location.href = barra.dataset.detalle;
  });

  // --- Refrescar la grilla sin perder la posición del scroll --------------
  async function refrescar() {
    const { scrollLeft, scrollTop } = scroll;
    const respuesta = await fetch(scroll.dataset.urlGrilla);
    if (respuesta.redirected) {
      location.href = respuesta.url; // sesión vencida
      return;
    }
    scroll.innerHTML = await respuesta.text();
    scroll.scrollLeft = scrollLeft;
    scroll.scrollTop = scrollTop;
    aplicarBusqueda();
  }

  // --- Buscador: atenúa las reservas que no coinciden ----------------------
  function aplicarBusqueda() {
    const texto = buscador.value.trim().toLowerCase();
    scroll.querySelectorAll(".barra-reserva[data-busqueda]").forEach((barra) => {
      barra.classList.toggle("barra-reserva--atenuada", Boolean(texto) && !barra.dataset.busqueda.includes(texto));
    });
  }

  buscador.addEventListener("input", aplicarBusqueda);
})();
