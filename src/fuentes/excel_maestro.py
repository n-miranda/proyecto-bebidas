"""Maestro de productos: proveedor, rubro y unidades por bulto (CLAUDE.md
seccion 4.3 y seccion 13, pregunta 2).

Fuente autoritativa de proveedor y rubro: STOCK\\rubros.xlsx (confirmado
2026-09-10 -- productos.xlsx tiene nombres de proveedor desactualizados para
varios codigos, ej. articulos de Danone que ahi figuraban como Mastellone).
productos.xlsx (C:\\integracion_stock\\auxiliares\\productos.xlsx, hoja
"Codigos", compartido con D:\\AUTOMATIZACION_PEDIDOS_CONTROL) se usa solo
para unidades por bulto, y como respaldo de proveedor para los pocos codigos
que no estan en rubros.xlsx.

Segundo respaldo de unidades por bulto (pedido del usuario, 2026-09-10): las
planillas de pedido de Supply\\Posadas\\2. Pedidos Posadas\\<proveedor>\\ traen
su propia columna de UxB (confirmado para los 5 proveedores con carpeta:
La Serenisima, GEORGALOS, Piamontesa, TIMBO, TRIGOS ARGENTINOS). Se usa el
archivo mas reciente por fecha de modificacion de cada carpeta (sin bajar a
sus subcarpetas, que son archivo por periodo/temporada viejo) para completar
codigos que ni rubros.xlsx ni productos.xlsx tienen cargados. Es un respaldo
best-effort: si una carpeta o archivo no esta, o cambia de estructura, la
app sigue funcionando igual (esos codigos quedan con UxB=1 como antes).
"""
from __future__ import annotations

import logging
from pathlib import Path

import openpyxl
import pandas as pd

from src.conversion import normalizar_codigo
from src.fuentes.base import FuenteMaestroProductos

logger = logging.getLogger(__name__)

PROVEEDOR_SIN_CLASIFICAR = "SIN CLASIFICAR"
RUBRO_SIN_CLASIFICAR = "SIN CLASIFICAR"


# Los acentos de RUBRO (ej. "LACTEOS") se ven como '?' en la consola de
# Windows (codepagina cp1252, no soporta 'A'), pero el dato en el Excel esta
# bien codificado en UTF-8 -- no hace falta ninguna correccion, esto es solo
# una limitacion de visualizacion de la terminal de diagnostico.
def _corregir_mojibake(texto: str) -> str:
    return texto


# (subcarpeta dentro de supply_pedidos_carpeta, hoja, fila de encabezado,
#  columna de codigo, columna de UxB) -- confirmado contra el archivo mas
#  reciente de cada proveedor, 2026-09-10.
_FUENTES_UXB_PEDIDOS = [
    ("La Serenisima", "PLANILLA PEDIDOS", 6, 2, 8),
    ("GEORGALOS", "Pedido GEORGALOS", 6, 2, 4),
    ("Piamontesa", "PEDIDO", 12, 2, 4),
    ("TIMBO", "Pedido TIMBO", 6, 2, 4),
    ("TRIGOS ARGENTINOS", "Pedido Salteña", 6, 1, 3),
]


class ExcelMaestroProductos(FuenteMaestroProductos):
    def __init__(self, ruta_productos: Path, ruta_rubros: Path, carpeta_pedidos_posadas: Path | None = None):
        self.ruta_productos = ruta_productos
        self.ruta_rubros = ruta_rubros
        self.carpeta_pedidos_posadas = carpeta_pedidos_posadas

    def _leer_uxb(self) -> pd.DataFrame:
        """Unidades por bulto, mas un proveedor de respaldo (columna E) para
        cuando el codigo no esta en rubros.xlsx. El proveedor autoritativo
        sale de _leer_rubros_y_proveedor."""
        if not self.ruta_productos.exists():
            raise FileNotFoundError(
                f"No se encontro el maestro de productos: {self.ruta_productos}"
            )
        wb = openpyxl.load_workbook(self.ruta_productos, data_only=True, read_only=True)
        ws = wb["Codigos"]
        filas = []
        vistos = set()
        duplicados = 0
        for row in ws.iter_rows(min_row=2, max_col=6, values_only=True):
            codigo_raw, _desc, _prov_cod, _cod_prov_chess, proveedor, uxb = row
            if codigo_raw is None:
                continue
            codigo = normalizar_codigo(codigo_raw)
            if codigo in vistos:
                duplicados += 1
                continue
            vistos.add(codigo)
            filas.append({
                "codigo": codigo,
                "proveedor_respaldo": (proveedor or "").strip() if isinstance(proveedor, str) else proveedor,
                "unidades_por_bulto": float(uxb) if uxb else None,
            })
        wb.close()
        if duplicados:
            logger.info("Maestro productos: %d codigos duplicados descartados (se usa la primera ocurrencia)", duplicados)
        df = pd.DataFrame(filas, columns=["codigo", "proveedor_respaldo", "unidades_por_bulto"])
        logger.info("Maestro productos: archivo=%s filas_utiles=%d", self.ruta_productos.name, len(df))
        return df

    def _leer_rubros_y_proveedor(self) -> pd.DataFrame:
        """Rubro (columna C) y proveedor (columna D) -- fuente autoritativa
        de ambos, ver docstring del modulo."""
        if not self.ruta_rubros.exists():
            raise FileNotFoundError(f"No se encontro el archivo de rubros: {self.ruta_rubros}")
        wb = openpyxl.load_workbook(self.ruta_rubros, data_only=True, read_only=True)
        ws = wb[wb.sheetnames[0]]
        filas = []
        vistos = set()
        duplicados = 0
        for codigo_raw, _desc, rubro, proveedor in ws.iter_rows(min_row=2, max_col=4, values_only=True):
            if codigo_raw is None:
                continue
            codigo = normalizar_codigo(codigo_raw)
            if codigo in vistos:
                duplicados += 1
                continue
            vistos.add(codigo)
            filas.append({
                "codigo": codigo,
                "rubro": _corregir_mojibake(rubro.strip()) if isinstance(rubro, str) else rubro,
                "proveedor": proveedor.strip() if isinstance(proveedor, str) else proveedor,
            })
        wb.close()
        if duplicados:
            logger.info("Rubros: %d codigos duplicados descartados (se usa la primera ocurrencia)", duplicados)
        df = pd.DataFrame(filas, columns=["codigo", "rubro", "proveedor"])
        logger.info("Rubros: archivo=%s filas=%d", self.ruta_rubros.name, len(df))
        return df

    def _archivo_mas_reciente(self, carpeta: Path) -> Path | None:
        """Solo archivos directos de la carpeta -- nunca baja a subcarpetas
        (ahi suelen vivir pedidos viejos de temporadas/periodos anteriores)."""
        if not carpeta.exists():
            return None
        candidatos = [p for p in carpeta.glob("*.xlsx") if p.is_file() and not p.name.startswith("~$")]
        if not candidatos:
            return None
        return max(candidatos, key=lambda p: p.stat().st_mtime)

    def _leer_uxb_de_pedido(self, subcarpeta: str, hoja: str, header_row: int, col_codigo: int, col_uxb: int) -> dict[str, float]:
        """Lee codigo/UxB del pedido mas reciente de una carpeta de
        proveedor. Best-effort: cualquier problema (carpeta ausente, hoja
        renombrada, etc.) se loguea y devuelve vacio en vez de romper la
        carga -- ver docstring del modulo."""
        if self.carpeta_pedidos_posadas is None:
            return {}
        try:
            elegido = self._archivo_mas_reciente(self.carpeta_pedidos_posadas / subcarpeta)
            if elegido is None:
                return {}

            wb = openpyxl.load_workbook(elegido, data_only=True, read_only=True)
            ws = wb[hoja]
            max_col = max(col_codigo, col_uxb)
            uxb_por_codigo: dict[str, float] = {}
            for row in ws.iter_rows(min_row=header_row + 1, max_col=max_col, values_only=True):
                codigo_raw, uxb = row[col_codigo - 1], row[col_uxb - 1]
                if codigo_raw is None or uxb is None:
                    continue
                try:
                    codigo = normalizar_codigo(codigo_raw)
                    uxb_por_codigo[codigo] = float(uxb)
                except (ValueError, TypeError):
                    continue
            wb.close()
            logger.info(
                "Respaldo UxB %s: archivo=%s codigos_utiles=%d",
                subcarpeta, elegido.name, len(uxb_por_codigo),
            )
            return uxb_por_codigo
        except Exception as exc:  # noqa: BLE001 - respaldo best-effort, nunca debe romper la carga
            logger.warning("No se pudo leer el respaldo de UxB de %s: %s", subcarpeta, exc)
            return {}

    def _leer_uxb_respaldo_pedidos(self) -> dict[str, float]:
        combinado: dict[str, float] = {}
        for subcarpeta, hoja, header_row, col_codigo, col_uxb in _FUENTES_UXB_PEDIDOS:
            combinado.update(self._leer_uxb_de_pedido(subcarpeta, hoja, header_row, col_codigo, col_uxb))
        return combinado

    def leer(self) -> pd.DataFrame:
        uxb = self._leer_uxb()
        rubros = self._leer_rubros_y_proveedor()
        df = rubros.merge(uxb, on="codigo", how="outer")

        def _con_dato(valor) -> bool:
            return isinstance(valor, str) and valor.strip() != ""

        usa_respaldo = ~df["proveedor"].apply(_con_dato) & df["proveedor_respaldo"].apply(_con_dato)
        if usa_respaldo.any():
            logger.info(
                "Proveedor: %d codigos sin dato en rubros.xlsx, se completan con productos.xlsx",
                int(usa_respaldo.sum()),
            )
        df.loc[usa_respaldo, "proveedor"] = df.loc[usa_respaldo, "proveedor_respaldo"]
        df = df.drop(columns=["proveedor_respaldo"])

        uxb_pedidos = self._leer_uxb_respaldo_pedidos()
        if uxb_pedidos:
            falta_uxb = df["unidades_por_bulto"].isna() | (df["unidades_por_bulto"] == 0)
            completar = falta_uxb & df["codigo"].isin(uxb_pedidos)
            if completar.any():
                logger.info(
                    "UxB: %d codigos completados con los respaldos de pedidos por proveedor",
                    int(completar.sum()),
                )
            df.loc[completar, "unidades_por_bulto"] = df.loc[completar, "codigo"].map(uxb_pedidos)

        return df
