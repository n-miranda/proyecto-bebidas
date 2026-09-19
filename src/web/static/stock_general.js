(() => {
  "use strict";

  const fmtDosDecimales = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const encabezadoTabla = document.getElementById("encabezado-tabla");
  const cuerpoTabla = document.getElementById("cuerpo-tabla");
  const fechaActualizacionEl = document.getElementById("fecha-actualizacion");
  const totalesEl = document.getElementById("totales");
  const inputBuscador = document.getElementById("filtro-buscador");
  const btnExportarExcel = document.getElementById("btn-exportar-excel");

  let todasLasFilas = [];
  let depositos = [];

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

  function filasFiltradas() {
    const busqueda = inputBuscador.value.trim().toLowerCase();
    if (!busqueda) return todasLasFilas;
    return todasLasFilas.filter((fila) =>
      fila.codigo.toLowerCase().includes(busqueda) ||
      fila.descripcion.toLowerCase().includes(busqueda)
    );
  }

  function renderEncabezado() {
    encabezadoTabla.innerHTML = `
      <tr>
        <th>Código</th>
        <th>Descripción</th>
        ${depositos.map((d) => `<th class="num">${escaparHtml(d)} (bultos)</th>`).join("")}
        <th class="num">Tránsito (bultos)</th>
        <th>Novedad</th>
      </tr>`;
  }

  function render() {
    const filas = filasFiltradas();

    if (filas.length === 0) {
      cuerpoTabla.innerHTML = `<tr><td colspan="${4 + depositos.length}">No hay artículos que coincidan con la búsqueda.</td></tr>`;
    } else {
      cuerpoTabla.innerHTML = filas.map((fila) => `
      <tr>
        <td>${fila.codigo}</td>
        <td title="${escaparHtml(fila.descripcion)}">${fila.descripcion}</td>
        ${depositos.map((d) => `<td class="num">${fmtDosDecimales.format(fila.stockPorDeposito[d] ?? 0)}</td>`).join("")}
        <td class="num">${fmtDosDecimales.format(fila.transitoTotal)}</td>
        <td>${escaparHtml(fila.novedad)}</td>
      </tr>`).join("");
    }

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
