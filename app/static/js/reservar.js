// Formulario de reserva del sitio público: resumen en vivo y ayudas chicas.
// El servidor valida todo de nuevo (app/services/reservas.py → crear_reserva_web).
(function () {
  const form = document.getElementById("form-reserva");
  if (!form) return;

  const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const DIA_MS = 86400000;
  const entrada = form.elements.entrada;
  const salida = form.elements.salida;
  const resumen = {
    imagen: document.getElementById("resumen-imagen"),
    nombre: document.getElementById("resumen-nombre"),
    fechas: document.getElementById("resumen-fechas"),
    noches: document.getElementById("resumen-noches"),
    precio: document.getElementById("resumen-precio"),
    total: document.getElementById("resumen-total"),
  };

  const moneda = (valor) => `${window.MONEDA || "$"} ${valor.toLocaleString("es-AR")}`;
  const aMs = (iso) => {
    const [anio, mes, dia] = iso.split("-").map(Number);
    return Date.UTC(anio, mes - 1, dia);
  };
  const corta = (ms) => {
    const fecha = new Date(ms);
    return `${fecha.getUTCDate()} ${MESES[fecha.getUTCMonth()]}`;
  };

  function tipoElegido() {
    return form.querySelector('input[name="tipo"]:checked');
  }

  // Las opciones de personas que no entran en la habitación elegida se deshabilitan
  function limitarPersonas(capacidad) {
    const opciones = [...form.querySelectorAll('input[name="personas"]')];
    opciones.forEach((opcion) => {
      opcion.disabled = Number(opcion.value) > capacidad;
    });
    const marcada = opciones.find((o) => o.checked);
    if (!marcada || marcada.disabled) opciones[Math.min(capacidad, 2) - 1].checked = true;
  }

  function actualizar() {
    const tipo = tipoElegido();
    if (!tipo) return;
    limitarPersonas(Number(tipo.dataset.capacidad));

    const precio = Number(tipo.dataset.precio);
    // Un tipo puede no tener foto: en ese caso se oculta la miniatura
    if (tipo.dataset.imagen) resumen.imagen.src = tipo.dataset.imagen;
    resumen.imagen.hidden = !tipo.dataset.imagen;
    resumen.nombre.textContent = tipo.dataset.nombre;
    resumen.precio.textContent = moneda(precio);

    const noches = entrada.value && salida.value ? Math.round((aMs(salida.value) - aMs(entrada.value)) / DIA_MS) : 0;
    if (noches > 0) {
      resumen.fechas.textContent = `${corta(aMs(entrada.value))} al ${corta(aMs(salida.value))}`;
      resumen.noches.textContent = noches;
      resumen.total.textContent = moneda(precio * noches);
    } else {
      resumen.fechas.textContent = resumen.noches.textContent = resumen.total.textContent = "—";
    }
  }

  // Si la salida queda antes de la llegada, se corre al día siguiente
  entrada.addEventListener("change", () => {
    if (!entrada.value) return;
    const minimo = new Date(aMs(entrada.value) + DIA_MS).toISOString().slice(0, 10);
    salida.min = minimo;
    if (!salida.value || salida.value < minimo) salida.value = minimo;
  });

  form.addEventListener("change", actualizar);
  form.addEventListener("input", actualizar);
  actualizar();
})();
