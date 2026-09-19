(() => {
  "use strict";

  const fmtDosDecimales = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const encabezadoTabla = document.getElementById("encabezado-tabla");
  const cuerpoTabla = document.getElementById("cuerpo-tabla");
  const fechaActualizacionEl = document.getElementById("fecha-actualizacion");
  const totalesEl = document.getElementById("totales");
  const inputBuscador = document.getElementById("filtro-buscador");
  const btnExportarExcel = document.getElementById("btn-exportar-excel");

  const subtituloEl = document.getElementById("tabla-subtitulo");

  let todasLasFilas = [];
  let depositos = [];

  // Sin orden por defecto (queda por codigo, como llega). Cada clic en un
  // encabezado recorre asc -> desc -> sin orden, igual que la tabla principal.
  let ordenCampo = null;
  let ordenAscendente = true;

  function escaparHtml(texto) {
    return String(texto)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Un mismo codigo puede traer una fila por deposito (ver consolidador.py):
  // se agrupa por codigo y el stock de cada deposito pasa a ser una columna
  // propia, en vez de una fila aparte -- para que los depositos se vean
  // uno al lado del otro.
  function agruparPorCodigo(articulos) {
    const porCodigo = new Map();
    for (const art of articulos) {
      if (art.deposito === "SIN DEPOSITO") continue;
      if (!porCodigo.has(art.codigo)) {
        porCodigo.set(art.codigo, {
          codigo: art.codigo, descripcion: art.descripcion, novedad: art.novedad || "",
          transitoTotal: 0, stockPorDeposito: {},
        });
      }
      const fila = porCodigo.get(art.codigo);
      fila.stockPorDeposito[art.deposito] = art.stock_bultos;
      // Transito ya viene por (codigo, deposito) -- ver consolidador.py --
      // aca se suma entre depositos porque esta vista es un resumen por
      // codigo, no tiene una columna por deposito para el transito.
      fila.transitoTotal += art.transito_bultos || 0;
    }
    return [...porCodigo.values()].sort((a, b) => Number(a.codigo) - Number(b.codigo));
  }

  function depositosPresentes(filas) {
    const set = new Set();
    for (const fila of filas) {
      for (const deposito of Object.keys(fila.stockPorDeposito)) set.add(deposito);
    }
    return [...set].sort((a, b) => a.localeCompare(b, "es"));
  }

  // "dep:OB" = columna de stock del deposito OB; el resto usa el nombre del campo.
  function columnas() {
    return [
      { campo: "codigo", etiqueta: "Código" },
      { campo: "descripcion", etiqueta: "Descripción", texto: true },
      ...depositos.map((d) => ({ campo: `dep:${d}`, etiqueta: `${d} (bultos)`, num: true })),
      { campo: "transito", etiqueta: "Tránsito (bultos)", num: true },
      { campo: "novedad", etiqueta: "Novedad", texto: true },
    ];
  }

  function valorOrden(fila, campo) {
    if (campo === "codigo") return Number(fila.codigo);
    if (campo === "descripcion") return fila.descripcion.toLowerCase();
    if (campo === "transito") return fila.transitoTotal;
    if (campo === "novedad") return fila.novedad ? fila.novedad.toLowerCase() : null;
    return fila.stockPorDeposito[campo.slice(4)] ?? 0;
  }

  function ordenar(filas) {
    if (!ordenCampo) return [...filas];
    return [...filas].sort((a, b) => {
      const va = valorOrden(a, ordenCampo);
      const vb = valorOrden(b, ordenCampo);
      // Sin dato (ej. sin novedad) siempre al final, asc o desc.
      if (va === null || vb === null) return va === vb ? 0 : (va === null ? 1 : -1);
      if (va < vb) return ordenAscendente ? -1 : 1;
      if (va > vb) return ordenAscendente ? 1 : -1;
      return 0;
    });
  }

  // Filas segun la busqueda y el orden vigentes: es lo que se ve en pantalla
  // y lo que exporta "Exportar a Excel".
  function filasFiltradas() {
    const busqueda = inputBuscador.value.trim().toLowerCase();
    const base = !busqueda
      ? todasLasFilas
      : todasLasFilas.filter((fila) =>
        fila.codigo.toLowerCase().includes(busqueda) ||
        fila.descripcion.toLowerCase().includes(busqueda)
      );
    return ordenar(base);
  }

  function textoOrdenActual() {
    if (!ordenCampo) return "sin ordenar";
    const col = columnas().find((c) => c.campo === ordenCampo);
    const sentido = col.texto
      ? (ordenAscendente ? "de A a Z" : "de Z a A")
      : (ordenAscendente ? "de menor a mayor" : "de mayor a menor");
    // Los depositos (OB, PR...) son codigos: se dejan en mayusculas.
    const nombre = ordenCampo.startsWith("dep:") ? col.etiqueta : col.etiqueta.toLowerCase();
    return `ordenado por ${nombre}, ${sentido}`;
  }

  function renderEncabezado() {
    encabezadoTabla.innerHTML = "<tr>" + columnas().map((c) => {
      const activa = c.campo === ordenCampo;
      const clases = [c.num ? "num" : "", activa ? "orden-activo" : "", activa && !ordenAscendente ? "orden-desc" : ""]
        .filter(Boolean).join(" ");
      const aria = !activa ? "none" : (ordenAscendente ? "ascending" : "descending");
      const titulo = !activa
        ? (c.texto ? "Ordenar de A a Z" : "Ordenar de menor a mayor")
        : (ordenAscendente ? (c.texto ? "Ordenar de Z a A" : "Ordenar de mayor a menor") : "Quitar el orden");
      return `<th data-campo="${escaparHtml(c.campo)}"${clases ? ` class="${clases}"` : ""} aria-sort="${aria}" title="${titulo}">${escaparHtml(c.etiqueta)}</th>`;
    }).join("") + "</tr>";
  }

  encabezadoTabla.addEventListener("click", (ev) => {
    const th = ev.target.closest("th[data-campo]");
    if (!th) return;
    const campo = th.dataset.campo;
    if (campo !== ordenCampo) {
      ordenCampo = campo;
      ordenAscendente = true;
    } else if (ordenAscendente) {
      ordenAscendente = false;
    } else {
      ordenCampo = null;
      ordenAscendente = true;
    }
    renderEncabezado();
    render();
  });

  function render() {
    const filas = filasFiltradas();

    if (filas.length === 0) {
      cuerpoTabla.innerHTML = `<tr><td colspan="${4 + depositos.length}">No hay artículos que coincidan con la búsqueda.</td></tr>`;
    } else {
      // La columna que ordena queda resaltada de punta a punta, igual que en
      // la tabla principal.
      const act = (campo, extra = "") => {
        const clases = [extra, campo === ordenCampo ? "orden-activo" : ""].filter(Boolean).join(" ");
        return clases ? ` class="${clases}"` : "";
      };
      cuerpoTabla.innerHTML = filas.map((fila) => `
      <tr>
        <td${act("codigo")}>${fila.codigo}</td>
        <td${act("descripcion")} title="${escaparHtml(fila.descripcion)}">${fila.descripcion}</td>
        ${depositos.map((d) => `<td${act(`dep:${d}`, "num")}>${fmtDosDecimales.format(fila.stockPorDeposito[d] ?? 0)}</td>`).join("")}
        <td${act("transito", "num")}>${fmtDosDecimales.format(fila.transitoTotal)}</td>
        <td${act("novedad", "novedad-celda")}>${escaparHtml(fila.novedad)}</td>
      </tr>`).join("");
    }

    subtituloEl.textContent =
      `${filas.length} ${filas.length === 1 ? "código" : "códigos"} · una fila por código y una columna por depósito · ${textoOrdenActual()}`;

    totalesEl.textContent = `${filas.length} de ${todasLasFilas.length} artículos`;
  }

  inputBuscador.addEventListener("input", render);

  function csvEscapar(texto) {
    const t = String(texto);
    return /[;"\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
  }

  // "Exportar Excel": mismo mecanismo que "Exportar CSV" de la tabla
  // principal (CSV con punto y coma + BOM UTF-8, que Excel en es-AR abre
  // directo) -- respeta la busqueda aplicada en este momento.
  function exportarExcel() {
    const filas = filasFiltradas();
    const encabezado = ["Código", "Descripción", ...depositos.map((d) => `${d} (bultos)`), "Tránsito (bultos)", "Novedad"].join(";");
    const lineas = filas.map((fila) => [
      csvEscapar(fila.codigo),
      csvEscapar(fila.descripcion),
      ...depositos.map((d) => fmtDosDecimales.format(fila.stockPorDeposito[d] ?? 0)),
      fmtDosDecimales.format(fila.transitoTotal),
      csvEscapar(fila.novedad),
    ].join(";"));
    const csv = "﻿" + [encabezado, ...lineas].join("\r\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const fecha = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `stock_general_${fecha}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  btnExportarExcel.addEventListener("click", exportarExcel);

  async function cargarTodo() {
    const [respStock, respMeta] = await Promise.all([
      fetch("/api/stock"),
      fetch("/api/meta"),
    ]);
    if (!respStock.ok || !respMeta.ok) {
      throw new Error("No se pudieron cargar los datos.");
    }
    const articulos = await respStock.json();
    const { meta } = await respMeta.json();

    const fecha = new Date(meta.fecha_actualizacion + "T00:00:00");
    fechaActualizacionEl.textContent = `Actualizado: ${fecha.toLocaleDateString("es-AR")}`;

    todasLasFilas = agruparPorCodigo(articulos);
    depositos = depositosPresentes(todasLasFilas);
    renderEncabezado();
    render();
  }

  cargarTodo().catch((err) => {
    cuerpoTabla.innerHTML = `<tr><td>No se pudieron cargar los artículos: ${err.message}</td></tr>`;
  });
})();
