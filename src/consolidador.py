"""Arma el DataFrame canonico final (CLAUDE.md seccion 4.5).

Universo de articulos = SOLO los codigos de stock_bebidas.xlsx (pedido del
usuario, 2026-09-18): VENTAS.xlsx y el transito siguen siendo de otro
catalogo (Total Refrigerados, heredado de UNIFICADOR_STOCK) y no aportan
articulos propios, solo datos (venta 7d, transito) para los codigos que SI
estan en el stock de bebidas -- si no matchean, esos campos quedan en 0.
Los codigos de stock que no matchean contra el maestro de productos
(proveedor / UxB / rubro) no se descartan: quedan con los valores por
defecto de la seccion 4.5 y se listan en el reporte de inconsistencias.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from src.calendario import ventana_dias_venta
from src.config import Config
from src.conversion import calcular_dias_stock, clasificar_riesgo, convertir_a_bultos
from src.fuentes.excel_maestro import (
    PROVEEDOR_SIN_CLASIFICAR,
    RUBRO_SIN_CLASIFICAR,
    ExcelMaestroProductos,
)
from src.fuentes.excel_stock import ExcelStock
from src.fuentes.excel_transito import TransitoSupplyIngresos
from src.fuentes.excel_ventas import ExcelVentas

logger = logging.getLogger(__name__)

COLUMNAS_CANONICAS = [
    "codigo", "descripcion", "deposito", "proveedor", "rubro", "unidades_por_bulto",
    "stock_unidades", "stock_bultos", "venta_unidades_7d",
    "venta_promedio_bulto", "dias_stock",
    "transito_bultos", "dias_stock_c_transito", "dias_venta_usados",
    "clase_riesgo", "sin_clasificar",
]


@dataclass
class ResultadoConsolidacion:
    df: pd.DataFrame
    inconsistencias: list[dict] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)




def consolidar(config: Config, fecha_referencia: date | None = None) -> ResultadoConsolidacion:
    fecha_referencia = fecha_referencia or date.today()
    inconsistencias: list[dict] = []
    avisos: list[str] = []

    dias_venta = ventana_dias_venta(
        fecha_referencia,
        n=config.calculo.ventana_dias_venta,
        incluir_dia_actual=config.calculo.incluir_dia_actual,
        contar_dias_turisticos=config.calculo.contar_dias_turisticos,
    )
    logger.info("Ventana de %d dias de venta: %s", len(dias_venta), [d.isoformat() for d in dias_venta])

    stock_df = ExcelStock(config.rutas.stock_bebidas_archivo).leer()

    try:
        maestro_df = ExcelMaestroProductos(
            config.rutas.maestro_productos,
            config.rutas.stock_carpeta / config.rutas.rubros_archivo,
            config.rutas.supply_pedidos_carpeta,
        ).leer()
    except FileNotFoundError as exc:
        avisos.append(f"No se pudo leer el maestro de productos: {exc}. Todo articulo queda SIN CLASIFICAR.")
        maestro_df = pd.DataFrame(columns=["codigo", "proveedor", "unidades_por_bulto", "rubro"])

    ventas_df = ExcelVentas(config.rutas.ventas_carpeta).leer()

    fuente_transito = TransitoSupplyIngresos(
        supply_pedidos_carpeta=config.rutas.supply_pedidos_carpeta,
        ingresos_archivo=config.rutas.transito_carpeta / config.rutas.ingresos_archivo,
        estado_carpeta=config.rutas.salida,
        dias_vencimiento=config.transito.dias_vencimiento_pendiente,
    )
    try:
        transito_df = fuente_transito.leer()
    except Exception as exc:  # noqa: BLE001 - error esperable de datos, se reporta en castellano
        avisos.append(f"No se pudo leer transito: {exc}. Se usa transito=0.")
        transito_df = pd.DataFrame(columns=["codigo", "transito_unidades"])
    inconsistencias_transito = fuente_transito.inconsistencias()

    ventas_ventana = ventas_df[ventas_df["fecha"].isin(dias_venta)] if not ventas_df.empty else ventas_df
    ventas_agg = (
        ventas_ventana.groupby("codigo", as_index=False)["unidades_vendidas"]
        .sum()
        .rename(columns={"unidades_vendidas": "venta_unidades_7d"})
    )

    if ventas_df.empty:
        dias_venta_usados = 0
        avisos.append("No hay datos de ventas: 'Venta 7d' se calcula como si no hubiera venta.")
    else:
        fechas_disponibles = set(ventas_df["fecha"].unique())
        dias_venta_usados = sum(1 for d in dias_venta if d in fechas_disponibles)
        if dias_venta_usados < len(dias_venta):
            avisos.append(
                f"Los datos de VENTAS solo cubren {dias_venta_usados} de los "
                f"{len(dias_venta)} dias de venta de la ventana; 'Venta 7d' puede estar subestimada "
                "(no afecta 'dias de stock', que usa venta_promedio_bulto de stock_bebidas.xlsx)."
            )

    transito_agg = (
        transito_df.groupby("codigo", as_index=False)["transito_unidades"].sum()
        if not transito_df.empty else pd.DataFrame(columns=["codigo", "transito_unidades"])
    )

    # Universo de articulos = SOLO los codigos de stock_bebidas.xlsx (pedido
    # del usuario, 2026-09-18): antes se agregaban ademas los codigos que
    # aparecian unicamente en VENTAS.xlsx o transito, pero esas dos fuentes
    # siguen siendo de otro catalogo (Total Refrigerados) -- agregarlos
    # mostraba articulos ajenos a bebidas. stock_df puede traer el mismo
    # codigo dos veces (una fila por deposito, ver excel_stock.py); cada
    # (codigo, deposito) queda como su propia fila.
    df = stock_df.merge(maestro_df, on="codigo", how="left")
    df = df.merge(ventas_agg, on="codigo", how="left")
    df = df.merge(transito_agg, on="codigo", how="left")

    codigos_en_mas_de_un_deposito = (
        df.groupby("codigo")["deposito"].nunique().gt(1).sum()
    )
    if codigos_en_mas_de_un_deposito:
        avisos.append(
            f"{codigos_en_mas_de_un_deposito} articulos tienen stock en mas de un deposito: "
            "aparecen en una fila por deposito, cada una con su propio stock y venta promedio "
            "bulto (columna K de stock_bebidas.xlsx). 'Venta 7d' y 'transito' si usan el TOTAL "
            "del articulo, no discriminan por deposito (VENTAS.xlsx y el transito no lo traen)."
        )

    if config.proveedores_excluidos:
        excluidos = set(config.proveedores_excluidos)
        antes = len(df)
        df = df[~df["proveedor"].isin(excluidos)].reset_index(drop=True)
        cantidad_excluida = antes - len(df)
        if cantidad_excluida:
            logger.info(
                "Proveedores excluidos por configuracion (%s): %d articulos removidos",
                ", ".join(sorted(excluidos)), cantidad_excluida,
            )

    df["stock_unidades"] = df["stock_unidades"].fillna(0.0)
    df["venta_unidades_7d"] = df["venta_unidades_7d"].fillna(0.0)
    df["transito_unidades"] = df["transito_unidades"].fillna(0.0)
    df["descripcion"] = df["descripcion"].fillna("(sin descripcion)")
    df["sin_clasificar"] = False
    tiene_venta_promedio = df["venta_promedio_bulto"].notna()
    df["venta_promedio_bulto"] = df["venta_promedio_bulto"].fillna(0.0)

    for idx, row in df.iterrows():
        motivos = []
        if pd.isna(row["proveedor"]) or row["proveedor"] == "":
            df.at[idx, "proveedor"] = PROVEEDOR_SIN_CLASIFICAR
            motivos.append("sin proveedor en el maestro")
        if pd.isna(row["rubro"]) or row["rubro"] == "":
            df.at[idx, "rubro"] = RUBRO_SIN_CLASIFICAR
            motivos.append("sin rubro")
        if pd.isna(row["unidades_por_bulto"]) or not row["unidades_por_bulto"]:
            df.at[idx, "unidades_por_bulto"] = 1.0
            motivos.append("sin unidades por bulto (se usa 1)")
        if not tiene_venta_promedio[idx]:
            motivos.append("sin venta promedio bulto (no matchea contra la columna K/Cod del deposito)")
        if motivos:
            df.at[idx, "sin_clasificar"] = True
            inconsistencias.append({
                "codigo": row["codigo"],
                "descripcion": row["descripcion"],
                "motivo": "; ".join(motivos),
            })

    df["stock_bultos"] = df.apply(
        lambda r: convertir_a_bultos(r["stock_unidades"], r["unidades_por_bulto"]), axis=1
    )
    df["transito_bultos"] = df.apply(
        lambda r: convertir_a_bultos(r["transito_unidades"], r["unidades_por_bulto"]), axis=1
    )
    # dtype=object explicito: si se deja que pandas infiera el tipo, los
    # None que devuelve calcular_dias_stock (sin venta) se convierten
    # silenciosamente en NaN, que no es JSON valido (rompe el snapshot).
    # Base del calculo: venta_promedio_bulto (columna K de stock_bebidas.xlsx,
    # cruzada por deposito -- ver excel_stock.py), no el promedio diario de
    # VENTAS.xlsx (a pedido del usuario, 2026-09-17: esa base no matchea con
    # los codigos de bebidas todavia).
    df["dias_stock"] = pd.Series(
        [calcular_dias_stock(sb, vpb) for sb, vpb in zip(df["stock_bultos"], df["venta_promedio_bulto"])],
        index=df.index, dtype=object,
    )
    df["dias_stock_c_transito"] = pd.Series(
        [calcular_dias_stock(sb + tb, vpb) for sb, tb, vpb in
         zip(df["stock_bultos"], df["transito_bultos"], df["venta_promedio_bulto"])],
        index=df.index, dtype=object,
    )
    df["dias_venta_usados"] = dias_venta_usados

    # Politica de riesgo por producto (St Seg / D St): nunca se manda a la
    # web como columna, solo el color resultante en 'clase_riesgo'.
    politica_dias_stock = fuente_transito.leer_politica_dias_stock()
    df["clase_riesgo"] = [
        clasificar_riesgo(
            dias_stock=ds,
            dias_stock_seguridad=politica_dias_stock.get(codigo),
            rojo_hasta=config.semaforo_dias_stock.rojo_hasta,
            amarillo_hasta=config.semaforo_dias_stock.amarillo_hasta,
            verde_hasta=config.semaforo_dias_stock.verde_hasta,
            multiplo_amarillo=config.semaforo_relativo_stock_seguridad.amarillo_hasta_multiplo,
            multiplo_verde=config.semaforo_relativo_stock_seguridad.verde_hasta_multiplo,
        )
        for codigo, ds in zip(df["codigo"], df["dias_stock"])
    ]
    if politica_dias_stock:
        logger.info(
            "Politica de riesgo por producto (St Seg/D St): %d codigos con piso propio",
            len(politica_dias_stock),
        )

    df = df[COLUMNAS_CANONICAS]

    inconsistencias.extend(inconsistencias_transito)

    if inconsistencias:
        avisos.append(f"{len(inconsistencias)} inconsistencias detectadas (ver reporte).")
    logger.info(
        "Consolidacion: %d articulos, %d inconsistencias, %d avisos",
        len(df), len(inconsistencias), len(avisos),
    )

    meta = {
        "fecha_actualizacion": fecha_referencia.isoformat(),
        "dias_venta_ventana": [d.isoformat() for d in dias_venta],
        "dias_venta_usados": dias_venta_usados,
        "cantidad_articulos": len(df),
        "cantidad_inconsistencias": len(inconsistencias),
    }
    return ResultadoConsolidacion(df=df, inconsistencias=inconsistencias, avisos=avisos, meta=meta)
