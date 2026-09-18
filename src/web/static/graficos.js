(() => {
  "use strict";

  // Barras horizontales simples en HTML/CSS (no SVG/canvas): mas facil de
  // mantener y ya trae texto accesible/seleccionable. Sigue el metodo de la
  // skill dataviz -- marca fina con extremos redondeados, valor de cada
  // barra rotulado directo (no solo al pasar el mouse), tooltip como capa
  // adicional. Se usa en index.html para los graficos de "Articulos por
  // deposito" y "Estado de riesgo", ambos recalculados en cada render().

  const fmt = new Intl.NumberFormat("es-AR");
  const tooltip = document.getElementById("grafico-tooltip");

  function escaparHtml(texto) {
    return String(texto)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function posicionarTooltip(ev) {
    if (!tooltip) return;
    const margen = 14;
    let x = ev.clientX + margen;
    let y = ev.clientY + margen;
    // No dejar que el tooltip se corte contra el borde derecho/inferior.
    const anchoAprox = 200;
    const altoAprox = 32;
    if (x + anchoAprox > window.innerWidth) x = ev.clientX - anchoAprox - margen;
    if (y + altoAprox > window.innerHeight) y = ev.clientY - altoAprox - margen;
    tooltip.style.left = `${x}px`;
    tooltip.style.top = `${y}px`;
  }

  function mostrarTooltip(ev, texto) {
    if (!tooltip) return;
    tooltip.textContent = texto;
    tooltip.hidden = false;
    posicionarTooltip(ev);
  }

  function ocultarTooltip() {
    if (tooltip) tooltip.hidden = true;
  }

  function renderBarras(idContenedor, datos) {
    const contenedor = document.getElementById(idContenedor);
    if (!contenedor) return;

    const total = datos.reduce((acc, d) => acc + d.valor, 0);
    if (datos.length === 0 || total === 0) {
      contenedor.innerHTML = '<p class="grafico-vacio">Sin artículos para los filtros actuales.</p>';
      return;
    }

    const max = Math.max(...datos.map((d) => d.valor), 1);
    contenedor.innerHTML = datos.map((d) => {
      const pctBarra = (d.valor / max) * 100;
      const pctTotal = total > 0 ? (d.valor / total) * 100 : 0;
      const tip = `${d.etiqueta}: ${fmt.format(d.valor)} (${pctTotal.toFixed(1)}%)`;
      return `
      <div class="barra-fila" data-tooltip="${escaparHtml(tip)}">
        <span class="barra-etiqueta">${escaparHtml(d.etiqueta)}</span>
        <div class="barra-pista">
          <div class="barra-valor" style="width: ${pctBarra}%; background: ${d.color};"></div>
        </div>
        <span class="barra-numero">${fmt.format(d.valor)}</span>
      </div>`;
    }).join("");

    contenedor.querySelectorAll(".barra-fila").forEach((fila) => {
      const texto = fila.dataset.tooltip;
      fila.addEventListener("mouseenter", (ev) => mostrarTooltip(ev, texto));
      fila.addEventListener("mousemove", posicionarTooltip);
      fila.addEventListener("mouseleave", ocultarTooltip);
    });
  }

  window.Graficos = { renderBarras };
})();
