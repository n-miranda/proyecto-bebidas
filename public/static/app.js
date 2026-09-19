(() => {
  "use strict";

  const fmtEntero = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 0 });
  const fmtUnDecimal = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const fmtDosDecimales = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const COLUMNAS = [
    { campo: "codigo", etiqueta: "Código" },
    { campo: "descripcion", etiqueta: "Descripción" },
    { campo: "deposito", etiqueta: "Depósito" },
    { campo: "stock_bultos", etiqueta: "Stock (bultos)", num: true },
    { campo: "venta_promedio_bulto", etiqueta: "Venta prom. (bultos)", num: true },
    { campo: "dias_stock", etiqueta: "Días de stock", num: true },
    { campo: "transito_bultos", etiqueta: "Tránsito (bultos)", num: true },
    { campo: "dias_stock_c_transito", etiqueta: "Días stock c/tránsito", num: true },
  ];

  const ETIQUETA_COLUMNA = Object.fromEntries(COLUMNAS.map((c) => [c.campo, c.etiqueta]));

  let articulos = [];
  let ordenCampo = "dias_stock";
  let ordenAscendente = true;

  const cuerpoTabla = document.getElementById("cuerpo-tabla");
  const fechaActualizacionEl = document.getElementById("fecha-actualizacion");
  const ventanaVentasEl = document.getElementById("ventana-ventas");
  const avisosEl = document.getElementById("avisos");
  const totalesEl = document.getElementById("totales");
  const btnExportar = document.getElementById("btn-exportar");
  const btnExportarPdf = document.getElementById("btn-exportar-pdf");
  const btnExportarCantidadEl = document.getElementById("btn-exportar-cantidad");
  const btnExportarPdfCantidadEl = document.getElementById("btn-exportar-pdf-cantidad");
  const btnStockGeneral = document.getElementById("btn-stock-general");
  const inputBuscador = document.getElementById("filtro-buscador");
  const checkSinClasificar = document.getElementById("filtro-sin-clasificar");
  const contadorSinClasificarEl = document.getElementById("contador-sin-clasificar");
  const toastEl = document.getElementById("toast");
  const encabezadoImpresionFechaEl = document.getElementById("encabezado-impresion-fecha");
  const encabezadoImpresionFiltrosEl = document.getElementById("encabezado-impresion-filtros");
  const filtrosActivosEl = document.getElementById("filtros-activos");
  const tablaCantidadEl = document.getElementById("tabla-cantidad");
  const tablaOrdenDescEl = document.getElementById("tabla-orden-desc");
  const kpiTotalGeneralEl = document.getElementById("kpi-total-general");
  const kpiEls = {
    total: document.getElementById("kpi-total"),
    rojo: document.getElementById("kpi-rojo"),
    verde: document.getElementById("kpi-verde"),
    sobrestock: document.getElementById("kpi-sobrestock"),
  };
  const kpiCtaEls = {
    rojo: document.getElementById("kpi-rojo-cta"),
    verde: document.getElementById("kpi-verde-cta"),
    sobrestock: document.getElementById("kpi-sobrestock-cta"),
  };
  const valorPrevioKpi = { total: 0, rojo: 0, verde: 0, sobrestock: 0 };

  let toastTimeoutId = null;
  function mostrarToast(mensaje, tipo = "exito") {
    if (toastTimeoutId) clearTimeout(toastTimeoutId);
    toastEl.textContent = mensaje;
    toastEl.className = "toast" + (tipo === "error" ? " toast-error" : "");
    toastEl.hidden = false;
    toastTimeoutId = setTimeout(() => {
      toastEl.classList.add("toast-saliendo");
      setTimeout(() => { toastEl.hidden = true; }, 200);
    }, 3200);
  }

  function animarNumero(el, desde, hasta, duracionMs = 350) {
    if (desde === hasta) { el.textContent = fmtEntero.format(hasta); return; }
    const inicio = performance.now();
    function paso(ahora) {
      const t = Math.min(1, (ahora - inicio) / duracionMs);
      const suavizado = 1 - Math.pow(1 - t, 3);
      el.textContent = fmtEntero.format(Math.round(desde + (hasta - desde) * suavizado));
      if (t < 1) requestAnimationFrame(paso);
    }
    requestAnimationFrame(paso);
  }

  function crearMultiSelect(idContenedor, alCambiar) {
    const contenedor = document.getElementById(idContenedor);
    const boton = contenedor.querySelector(".multiselect-boton");
    const panel = contenedor.querySelector(".multiselect-panel");
    const opcionesEl = contenedor.querySelector(".multiselect-opciones");
    let opciones = [];
    let seleccion = new Set();

    function actualizarBoton() {
      if (opciones.length === 0 || seleccion.size === opciones.length) {
        boton.textContent = "Todos";
      } else if (seleccion.size === 0) {
        boton.textContent = "Ninguno";
      } else if (seleccion.size === 1) {
        boton.textContent = [...seleccion][0];
      } else {
        boton.textContent = `${seleccion.size} seleccionados`;
      }
    }

    function setOpciones(lista) {
      opciones = lista;
      seleccion = new Set(lista);
      opcionesEl.innerHTML = lista.map((v, i) => `
        <label class="multiselect-opcion">
          <input type="checkbox" data-indice="${i}" checked>
          <span>${v}</span>
        </label>
      `).join("");
      opcionesEl.querySelectorAll("input[type=checkbox]").forEach((cb) => {
        cb.addEventListener("change", () => {
          const valor = opciones[Number(cb.dataset.indice)];
          if (cb.checked) seleccion.add(valor); else seleccion.delete(valor);
          actualizarBoton();
          alCambiar();
        });
      });
      actualizarBoton();
    }

    boton.addEventListener("click", (ev) => {
      ev.stopPropagation();
      const estabaAbierto = !panel.hidden;
      document.querySelectorAll(".multiselect-panel").forEach((p) => { p.hidden = true; });
      panel.hidden = estabaAbierto;
    });

    contenedor.querySelector('[data-accion="todos"]').addEventListener("click", () => {
      seleccion = new Set(opciones);
      opcionesEl.querySelectorAll("input[type=checkbox]").forEach((cb) => { cb.checked = true; });
      actualizarBoton();
      alCambiar();
    });
    contenedor.querySelector('[data-accion="ninguno"]').addEventListener("click", () => {
      seleccion = new Set();
      opcionesEl.querySelectorAll("input[type=checkbox]").forEach((cb) => { cb.checked = false; });
      actualizarBoton();
      alCambiar();
    });

    return { setOpciones, getSeleccion: () => seleccion, getOpciones: () => opciones };
  }

  document.addEventListener("click", (ev) => {
    if (!ev.target.closest(".multiselect")) {
      document.querySelectorAll(".multiselect-panel").forEach((p) => { p.hidden = true; });
    }
  });

  const multiDeposito = crearMultiSelect("multiselect-deposito", () => render());
  const multiCluster = crearMultiSelect("multiselect-cluster", () => render());

  // Selector de columnas visibles (pedido del usuario, 2026-09-18). Solo
  // ofrece las columnas que existen HOY en COLUMNAS -- las que ya se sacaron
  // de la tabla (Proveedor, Rubro, Venta 7d) no vuelven a aparecer aca.
  const estiloColumnas = document.createElement("style");
  document.head.appendChild(estiloColumnas);
  const multiColumnas = crearMultiSelect("multiselect-columnas", () => aplicarColumnasVisibles());
  multiColumnas.setOpciones(COLUMNAS.map((c) => c.etiqueta));

  function aplicarColumnasVisibles() {
    const seleccion = multiColumnas.getSeleccion();
    const ocultas = COLUMNAS.filter((c) => !seleccion.has(c.etiqueta)).map((c) => c.campo);
    estiloColumnas.textContent = ocultas
      .map((campo) => `[data-campo="${campo}"] { display: none; }`)
      .join("\n");
  }

  function formatearDiasStock(valor, stockMasTransito) {
    if (valor === null || valor === undefined) {
      return stockMasTransito > 0 ? "S/V" : "—";
    }
    return fmtUnDecimal.format(valor);
  }

  // El color de riesgo ya viene resuelto del backend en 'clase_riesgo'
  // (tiene en cuenta el piso de stock de seguridad propio del producto
  // cuando existe, ver src/conversion.py::clasificar_riesgo). El frontend
  // solo lo traduce a la clase CSS correspondiente.
  function claseSemaforo(art) {
    return "semaforo-" + (art.clase_riesgo || "neutro");
  }

  function esCritico(art) {
    return art.clase_riesgo === "rojo";
  }

  function esQuiebreCubierto(art) {
    return esCritico(art) && art.transito_bultos > 0;
  }

  function valorCeldaTexto(art, campo) {
    switch (campo) {
      case "stock_bultos":
      case "venta_promedio_bulto":
      case "transito_bultos":
        return fmtDosDecimales.format(art[campo]);
      case "dias_stock":
        return formatearDiasStock(art.dias_stock, art.stock_bultos);
      case "dias_stock_c_transito":
        return formatearDiasStock(art.dias_stock_c_transito, art.stock_bultos + art.transito_bultos);
      default:
        return String(art[campo]);
    }
  }

  const SUFIJO_PUNTO = {
    "semaforo-rojo": "pe-rojo",
    "semaforo-amarillo": "pe-amarillo",
    "semaforo-verde": "pe-verde",
    "semaforo-sobrestock": "pe-sobrestock",
  };

  function puntoEstado(art) {
    const clase = SUFIJO_PUNTO[claseSemaforo(art)];
    return `<span class="punto-estado${clase ? " " + clase : ""}" title="${escaparHtml(ETIQUETA_ESTADO[claseSemaforo(art)] || "Sin venta")}"></span>`;
  }

  function poblarFiltros() {
    const depositos = [...new Set(articulos.map((a) => a.deposito))].sort((a, b) => a.localeCompare(b, "es"));
    multiDeposito.setOpciones(depositos);
    // Cluster: todavia no hay ese dato cargado en los articulos (pedido del
    // usuario, 2026-09-17) -- el filtro queda armado pero sin opciones hasta
    // que exista una fuente real. Ver el "size > 0" en filtrarSinEstado: con
    // cero opciones el filtro no excluye nada (si no, un Set vacio bloquearia
    // todas las filas).
    multiCluster.setOpciones([]);
    contadorSinClasificarEl.textContent = fmtEntero.format(
      articulos.filter((a) => a.sin_clasificar).length
    );
    kpiTotalGeneralEl.textContent = fmtEntero.format(articulos.length);
  }

  let filtroEstado = null; // null | "semaforo-rojo" | "semaforo-amarillo" | "semaforo-verde" | "semaforo-sobrestock"

  // Filtros "de contexto" (deposito/cluster/buscador), sin el filtro de estado -
  // los KPI se calculan sobre esto para que sigan mostrando el desglose
  // completo aunque haya un estado seleccionado (si no, al tocar "Rojo" el
  // resto de los KPI caerian a 0 y no se podria volver a elegir otro estado).
  function filtrarSinEstado(lista) {
    const depositos = multiDeposito.getSeleccion();
    const clusters = multiCluster.getSeleccion();
    const busqueda = inputBuscador.value.trim().toLowerCase();
    const soloSinClasificar = checkSinClasificar.checked;

    return lista.filter((a) => {
      if (soloSinClasificar && !a.sin_clasificar) return false;
      if (!depositos.has(a.deposito)) return false;
      if (clusters.size > 0 && !clusters.has(a.cluster)) return false;
      if (busqueda) {
        const enCodigo = a.codigo.toLowerCase().includes(busqueda);
        const enDescripcion = a.descripcion.toLowerCase().includes(busqueda);
        if (!enCodigo && !enDescripcion) return false;
      }
      return true;
    });
  }

  function filtrar(lista) {
    return filtrarSinEstado(lista).filter(
      (a) => !filtroEstado || claseSemaforo(a) === filtroEstado
    );
  }

  function aplicarFiltroEstado(estado) {
    filtroEstado = (filtroEstado === estado) ? null : estado;
    render();
  }

  // Resumen de filtros activos como chips removibles (modelo UX provisto
  // por el usuario, 2026-09-19): asi se ve de un vistazo que esta filtrado
  // sin tener que abrir cada multiselect, y se puede sacar uno solo.
  function marcarTodos(multi) {
    multi.setOpciones(multi.getOpciones());
  }

  function renderChipsFiltros() {
    const chips = [];

    if (multiDeposito.getSeleccion().size < multiDeposito.getOpciones().length) {
      chips.push({
        id: "deposito",
        texto: `Depósito: ${[...multiDeposito.getSeleccion()].sort((a, b) => a.localeCompare(b, "es")).join(", ") || "ninguno"}`,
      });
    }
    if (multiCluster.getOpciones().length > 0 && multiCluster.getSeleccion().size < multiCluster.getOpciones().length) {
      chips.push({
        id: "cluster",
        texto: `Clúster: ${[...multiCluster.getSeleccion()].sort((a, b) => a.localeCompare(b, "es")).join(", ") || "ninguno"}`,
      });
    }
    const busqueda = inputBuscador.value.trim();
    if (busqueda) chips.push({ id: "busqueda", texto: `Búsqueda: "${busqueda}"` });
    if (checkSinClasificar.checked) chips.push({ id: "sin-clasificar", texto: "Solo sin clasificar" });
    if (filtroEstado) chips.push({ id: "estado", texto: `Estado: ${ETIQUETA_ESTADO[filtroEstado] || filtroEstado}` });

    if (chips.length === 0) {
      filtrosActivosEl.innerHTML = "";
      return;
    }

    filtrosActivosEl.innerHTML =
      '<span class="filtros-activos-etiqueta">Filtros activos:</span>' +
      chips.map((c) => `
        <span class="chip-filtro">
          ${escaparHtml(c.texto)}
          <button type="button" data-quitar="${c.id}" aria-label="Quitar filtro">×</button>
        </span>`).join("") +
      '<button type="button" class="btn-limpiar-filtros" data-quitar="todo">Limpiar todo</button>';
  }

  filtrosActivosEl.addEventListener("click", (ev) => {
    const boton = ev.target.closest("[data-quitar]");
    if (!boton) return;
    switch (boton.dataset.quitar) {
      case "deposito": marcarTodos(multiDeposito); break;
      case "cluster": marcarTodos(multiCluster); break;
      case "busqueda": inputBuscador.value = ""; break;
      case "sin-clasificar": checkSinClasificar.checked = false; break;
      case "estado": filtroEstado = null; break;
      case "todo":
        marcarTodos(multiDeposito);
        marcarTodos(multiCluster);
        inputBuscador.value = "";
        checkSinClasificar.checked = false;
        filtroEstado = null;
        break;
    }
    render();
  });

  document.querySelectorAll(".kpi[data-estado]").forEach((el) => {
    const estado = el.dataset.estado || null;
    el.addEventListener("click", () => aplicarFiltroEstado(estado));
    el.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        aplicarFiltroEstado(estado);
      }
    });
  });

  checkSinClasificar.addEventListener("change", render);

  function ordenar(lista) {
    return [...lista].sort((a, b) => {
      let va = a[ordenCampo];
      let vb = b[ordenCampo];
      if (va === null || va === undefined) return 1;
      if (vb === null || vb === undefined) return -1;
      if (ordenCampo === "codigo") {
        va = Number(va);
        vb = Number(vb);
      } else if (typeof va === "string") {
        va = va.toLowerCase();
        vb = vb.toLowerCase();
      }
      if (va < vb) return ordenAscendente ? -1 : 1;
      if (va > vb) return ordenAscendente ? 1 : -1;
      return 0;
    });
  }

  function listaVisible() {
    return ordenar(filtrar(articulos));
  }

  function proveedorTopRiesgo(filasSinEstado) {
    const conteo = new Map();
    for (const a of filasSinEstado) {
      if (claseSemaforo(a) !== "semaforo-rojo") continue;
      conteo.set(a.proveedor, (conteo.get(a.proveedor) || 0) + 1);
    }
    let top = null;
    for (const entrada of conteo) {
      if (!top || entrada[1] > top[1]) top = entrada;
    }
    return top;
  }

  function renderKPIs(filasSinEstado) {
    const conteo = { total: filasSinEstado.length, rojo: 0, amarillo: 0, verde: 0, sobrestock: 0 };
    for (const a of filasSinEstado) {
      const clase = claseSemaforo(a);
      if (clase === "semaforo-rojo") conteo.rojo++;
      else if (clase === "semaforo-amarillo") conteo.amarillo++;
      else if (clase === "semaforo-verde") conteo.verde++;
      else if (clase === "semaforo-sobrestock") conteo.sobrestock++;
    }
    for (const clave of Object.keys(kpiEls)) {
      animarNumero(kpiEls[clave], valorPrevioKpi[clave], conteo[clave]);
      valorPrevioKpi[clave] = conteo[clave];
      if (kpiCtaEls[clave]) kpiCtaEls[clave].textContent = fmtEntero.format(conteo[clave]);
    }
    document.querySelectorAll(".kpi[data-estado]").forEach((el) => {
      const estado = el.dataset.estado || null;
      el.classList.toggle("kpi-activo", estado === filtroEstado);
    });
    return conteo;
  }

  // Graficos de resumen (panel arriba de los filtros): se recalculan con
  // cada render(), asi que siempre reflejan los filtros aplicados en ese
  // momento -- no es una foto fija del total sin filtrar.
  function renderGraficos(filasSinEstado, conteo) {
    if (!window.Graficos) return;

    const porDeposito = new Map();
    for (const a of filasSinEstado) {
      porDeposito.set(a.deposito, (porDeposito.get(a.deposito) || 0) + 1);
    }
    // Una sola magnitud por deposito (cantidad de articulos) -- un solo
    // color de acento, no una paleta categorica: no son "series" distintas,
    // es un ranking de la misma medida.
    const datosDeposito = [...porDeposito.entries()]
      .sort((a, b) => a[0].localeCompare(b[0], "es"))
      .map(([etiqueta, valor]) => ({ etiqueta, valor, color: "var(--acento)" }));
    window.Graficos.renderBarras("grafico-deposito", datosDeposito);

    const datosRiesgo = [
      { etiqueta: "Quiebre", valor: conteo.rojo, color: "var(--estado-critico)" },
      { etiqueta: "Normal", valor: conteo.verde, color: "var(--estado-bien)" },
      { etiqueta: "Sobrestock", valor: conteo.sobrestock, color: "var(--estado-sobrestock)" },
    ];
    window.Graficos.renderSegmentado("grafico-riesgo", datosRiesgo);
  }

  function celda(campo, art, extraClase = "") {
    const esNum = COLUMNAS.find((c) => c.campo === campo)?.num;
    const activa = campo === ordenCampo;
    const clases = [esNum ? "num" : "", extraClase, activa ? "orden-activo" : ""].filter(Boolean).join(" ");
    const texto = valorCeldaTexto(art, campo);
    const titleAttr = esNum ? ` title="${texto}"` : "";
    return `<td data-campo="${campo}"${clases ? ` class="${clases}"` : ""}${titleAttr}>${texto}</td>`;
  }

  function render() {
    const filas = listaVisible();

    if (filas.length === 0) {
      cuerpoTabla.innerHTML = '<tr><td colspan="9">No hay artículos que coincidan con los filtros.</td></tr>';
    } else {
      cuerpoTabla.innerHTML = filas.map((art, idx) => {
        const clase = claseSemaforo(art);
        const icono = esQuiebreCubierto(art) ? " " + ICONO_TRANSITO_SVG : "";
        // Escalonado suave: solo las primeras filas visibles a simple vista
        // se demoran un toque entre si, para que se note el efecto sin
        // hacer esperar en listas largas (filtrar 800 filas no debe tardar
        // "visualmente" 8 segundos en terminar de aparecer).
        const demora = Math.min(idx, 24) * 10;
        return `
      <tr class="${clase} fila-nueva" style="animation-delay: ${demora}ms">
        <td class="col-dot">${puntoEstado(art)}</td>
        <td data-campo="codigo"${ordenCampo === "codigo" ? ' class="orden-activo"' : ""}>${art.codigo}</td>
        <td data-campo="descripcion"${ordenCampo === "descripcion" ? ' class="orden-activo"' : ""} title="${escaparHtml(art.descripcion)}">${art.descripcion}</td>
        <td data-campo="deposito"${ordenCampo === "deposito" ? ' class="orden-activo"' : ""}>${art.deposito}</td>
        ${celda("stock_bultos", art)}
        ${celda("venta_promedio_bulto", art)}
        ${celda("dias_stock", art, "col-dias")}${icono}
        ${celda("transito_bultos", art)}
        ${celda("dias_stock_c_transito", art, "col-dias")}
      </tr>`;
      }).join("");
    }

    const filasSinEstado = filtrarSinEstado(articulos);
    const conteo = renderKPIs(filasSinEstado);
    renderGraficos(filasSinEstado, conteo);
    renderChipsFiltros();

    tablaCantidadEl.textContent = fmtEntero.format(filas.length);
    tablaOrdenDescEl.textContent =
      `ordenados por ${(ETIQUETA_COLUMNA[ordenCampo] || ordenCampo).toLowerCase()}, ` +
      (ordenAscendente ? "de menor a mayor" : "de mayor a menor");
    btnExportarCantidadEl.textContent = fmtEntero.format(filas.length);
    btnExportarPdfCantidadEl.textContent = fmtEntero.format(filas.length);

    const textoBase = filtroEstado
      ? `${filas.length} artículos filtrados (filtro de estado activo — click de nuevo en el KPI para quitarlo)`
      : `${filas.length} artículos filtrados`;

    const top = proveedorTopRiesgo(filasSinEstado);
    const resumenRiesgo = top
      ? `<span class="resumen-riesgo">Proveedor con más riesgo: <strong>${escaparHtml(top[0])}</strong> (${fmtEntero.format(top[1])} artículos)</span>`
      : "";
    totalesEl.innerHTML = `<span>${textoBase}</span>${resumenRiesgo}`;
  }

  function actualizarEncabezadosOrden() {
    document.querySelectorAll("th[data-campo]").forEach((th) => {
      th.classList.toggle("orden-activo", th.dataset.campo === ordenCampo);
      th.classList.toggle("orden-desc", th.dataset.campo === ordenCampo && !ordenAscendente);
    });
  }

  document.querySelectorAll("th[data-campo]").forEach((th) => {
    th.addEventListener("click", () => {
      const campo = th.dataset.campo;
      if (campo === ordenCampo) {
        ordenAscendente = !ordenAscendente;
      } else {
        ordenCampo = campo;
        ordenAscendente = true;
      }
      actualizarEncabezadosOrden();
      render();
    });
  });

  inputBuscador.addEventListener("input", render);

  const ICONO_AVISO_SVG =
    '<svg class="aviso-icono" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" ' +
    'stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.5L21.5 20H2.5z"/>' +
    '<line x1="12" y1="9.5" x2="12" y2="14"/><line x1="12" y1="16.8" x2="12" y2="16.81"/></svg>';

  function mostrarAvisos(avisos) {
    if (!avisos || avisos.length === 0) {
      avisosEl.hidden = true;
      return;
    }
    avisosEl.hidden = false;
    avisosEl.innerHTML = avisos
      .map((a) => `<div class="aviso-item">${ICONO_AVISO_SVG}<span>${escaparHtml(a)}</span></div>`)
      .join("");
  }

  function mostrarMeta(meta) {
    const fecha = new Date(meta.fecha_actualizacion + "T00:00:00");
    fechaActualizacionEl.textContent =
      `Actualizado: ${fecha.toLocaleDateString("es-AR")} — ${meta.cantidad_articulos} artículos, ` +
      `${meta.cantidad_inconsistencias} sin clasificar`;

    const dias = (meta.dias_venta_ventana || []).map((d) => new Date(d + "T00:00:00"));
    if (dias.length > 0) {
      const fmtCorta = (d) => d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit" });
      const fmtLarga = (d) => d.toLocaleDateString("es-AR");
      const desde = fmtCorta(dias[0]);
      const hasta = fmtCorta(dias[dias.length - 1]);
      ventanaVentasEl.textContent = `Ventas: ${desde} al ${hasta} (${meta.dias_venta_usados} días de venta)`;
      ventanaVentasEl.title = "Días de venta usados: " + dias.map(fmtLarga).join(", ");
    } else {
      ventanaVentasEl.textContent = "";
      ventanaVentasEl.title = "";
    }
  }

  function escaparHtml(texto) {
    return String(texto)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const ICONO_TRANSITO_SVG =
    '<svg class="icono-transito" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" ' +
    'stroke-linecap="round" stroke-linejoin="round"><title>Quiebre cubierto por tránsito</title>' +
    '<rect x="1" y="7" width="13" height="10"/><path d="M14 10h4l3 3v4h-7z"/>' +
    '<circle cx="6" cy="18.5" r="1.6"/><circle cx="17.5" cy="18.5" r="1.6"/></svg>';

  function csvEscapar(texto) {
    const t = String(texto);
    return /[;"\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
  }

  function exportarCSV() {
    const filas = listaVisible();
    const encabezado = COLUMNAS.map((c) => c.etiqueta).join(";");
    const lineas = filas.map((art) =>
      COLUMNAS.map((c) => csvEscapar(valorCeldaTexto(art, c.campo))).join(";")
    );
    const csv = "﻿" + [encabezado, ...lineas].join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const fecha = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `stock_${fecha}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  const ETIQUETA_ESTADO = {
    "semaforo-rojo": "Riesgo de quiebre",
    "semaforo-verde": "Normal",
    "semaforo-sobrestock": "Sobrestock",
  };

  // Como se ve la seleccion de un multiselect en el resumen del PDF: "Todos"
  // si no hay nada descartado (asi el que lo recibe sabe que es el universo
  // completo y no un recorte), la lista si es un subconjunto chico, o un
  // aviso si el filtro ni siquiera tiene opciones cargadas (caso Cluster).
  function etiquetaMultiselectPDF(multi) {
    const opciones = multi.getOpciones();
    const seleccion = multi.getSeleccion();
    if (opciones.length === 0) return "sin datos cargados todavía";
    if (seleccion.size === opciones.length) return "Todos";
    if (seleccion.size === 0) return "ninguno (0 artículos)";
    return [...seleccion].sort((a, b) => a.localeCompare(b, "es")).join(", ");
  }

  function resumenFiltrosPDF() {
    const partes = [
      `<strong>Depósito:</strong> ${escaparHtml(etiquetaMultiselectPDF(multiDeposito))}`,
      `<strong>Clúster:</strong> ${escaparHtml(etiquetaMultiselectPDF(multiCluster))}`,
    ];
    const busqueda = inputBuscador.value.trim();
    if (busqueda) partes.push(`<strong>Búsqueda:</strong> "${escaparHtml(busqueda)}"`);
    if (checkSinClasificar.checked) partes.push("<strong>Solo artículos sin clasificar</strong>");
    if (filtroEstado) {
      partes.push(`<strong>Estado:</strong> ${escaparHtml(ETIQUETA_ESTADO[filtroEstado] || filtroEstado)}`);
    }
    return partes.join(" &nbsp;•&nbsp; ");
  }

  function exportarPDF() {
    // El PDF sale del dialogo de impresion del navegador: la tabla en
    // pantalla YA esta filtrada/ordenada/con las columnas que el usuario
    // eligio, asi que imprimir tal cual (con una hoja de estilos @media
    // print que oculta todo lo que no sea la tabla) alcanza -- no hace
    // falta duplicar esa logica ni sumar una libreria de PDF. El
    // encabezado de impresion (oculto en pantalla) se completa recien aca,
    // con la fecha y los filtros vigentes en este momento.
    const ahora = new Date();
    encabezadoImpresionFechaEl.textContent =
      `Generado el ${ahora.toLocaleDateString("es-AR")} a las ${ahora.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" })} — ${listaVisible().length} artículos en este reporte`;
    encabezadoImpresionFiltrosEl.innerHTML = resumenFiltrosPDF();

    const tituloOriginal = document.title;
    document.title = `stock_bebidas_${ahora.toISOString().slice(0, 10)}`;
    window.print();
    document.title = tituloOriginal;
  }

  btnExportar.addEventListener("click", exportarCSV);
  btnExportarPdf.addEventListener("click", exportarPDF);
  btnStockGeneral.addEventListener("click", () => window.open("/stock-general", "_blank"));

  async function cargarTodo() {
    const [respStock, respMeta] = await Promise.all([
      fetch("/api/stock"),
      fetch("/api/meta"),
    ]);
    if (!respStock.ok || !respMeta.ok) {
      const detalle = await respMeta.json().catch(() => ({}));
      throw new Error(detalle.error || "No se pudieron cargar los datos.");
    }
    articulos = await respStock.json();
    const { meta } = await respMeta.json();
    mostrarMeta(meta);
    mostrarAvisos(meta.avisos);
    poblarFiltros();
    actualizarEncabezadosOrden();
    render();
  }

  cargarTodo().catch((err) => {
    mostrarToast("No se pudieron cargar los datos: " + err.message, "error");
    cuerpoTabla.innerHTML = '<tr><td colspan="9">No se pudieron cargar los artículos.</td></tr>';
  });
})();
