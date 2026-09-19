"""Lectura de TRANSITO\\<DEPOSITO> - Pedidos.xlsx (agregado 2026-09-19 a
pedido del usuario). Un archivo por deposito -- ej. "TC - Pedidos.xlsx",
"1. PR - Pedidos.xlsx", "sv - Pedidos.xlsx" -- el deposito se saca del
nombre del archivo (antes del " - "), sin importar mayusculas/minusculas
ni un prefijo numerado tipo "1. ".

Pestaña "Base" (busqueda case-insensitive del nombre): columnas por
posicion D=Remito, I=Cod., K=Pedido Original (Bultos). Un pedido sin
remito todavia (columna D vacia) esta pendiente de recibir -- esa
cantidad (columna K, YA esta en bultos, no en unidades) es lo que se suma
a transito_bultos para ese codigo+deposito en el consolidador. Si el
remito ya tiene numero, el pedido ya se desapcho/facturo y no cuenta como
transito pendiente (se omite, tal como pidio el usuario)."""
from __future__ import annotations

import logging
from pathlib import Path

import openpyxl
import pandas as pd

from src.conversion import normalizar_codigo

logger = logging.getLogger(__name__)

DEPOSITOS_VALIDOS = {"OB", "SV", "PR", "TC"}


def _deposito_desde_nombre(nombre_archivo: str) -> str | None:
    """'TC - Pedidos.xlsx' -> 'TC'; '1. PR - Pedidos.xlsx' -> 'PR';
    'sv - Pedidos.xlsx' -> 'SV'. None si no se puede identificar."""
    base = nombre_archivo.rsplit(".", 1)[0]
    antes_guion = base.split(" - ")[0].strip()
    palabras = antes_guion.split()
    if not palabras:
        return None
    token = palabras[-1].upper()
    return token if token in DEPOSITOS_VALIDOS else None


class TransitoPedidosDeposito:
    def __init__(self, carpeta: Path):
        self.carpeta = carpeta

    def _archivos(self) -> list[tuple[Path, str]]:
        if not self.carpeta.exists():
            return []
        encontrados = []
        for archivo in sorted(self.carpeta.glob("*.xlsx")):
            if archivo.name.startswith("~$"):
                continue
            if "pedidos" not in archivo.stem.lower():
                continue
            deposito = _deposito_desde_nombre(archivo.name)
            if deposito is None:
                logger.warning(
                    "PEDIDOS: no se pudo identificar el deposito de %s (se esperaba "
                    "'<DEPOSITO> - Pedidos.xlsx'), se omite", archivo.name,
                )
                continue
            encontrados.append((archivo, deposito))
        return encontrados

    def leer(self) -> pd.DataFrame:
        filas = []
        for archivo, deposito in self._archivos():
            wb = openpyxl.load_workbook(archivo, data_only=True, read_only=True)
            nombre_hoja = next((h for h in wb.sheetnames if h.strip().lower() == "base"), None)
            if nombre_hoja is None:
                logger.warning("PEDIDOS: %s no tiene pestaña 'Base', se omite", archivo.name)
                wb.close()
                continue
            ws = wb[nombre_hoja]
            leidas = 0
            pendientes = 0
            for fila in ws.iter_rows(min_row=2, max_col=11, values_only=True):
                remito, codigo_raw, cantidad = fila[3], fila[8], fila[10]
                if codigo_raw is None:
                    continue
                leidas += 1
                if remito is not None and str(remito).strip() != "":
                    continue  # ya tiene remito -> ya se despacho, no es transito pendiente
                if cantidad is None:
                    continue
                filas.append({
                    "codigo": normalizar_codigo(codigo_raw),
                    "deposito": deposito,
                    "transito_bultos_pedidos": float(cantidad),
                })
                pendientes += 1
            wb.close()
            logger.info(
                "PEDIDOS: archivo=%s deposito=%s filas=%d pendientes_sin_remito=%d",
                archivo.name, deposito, leidas, pendientes,
            )

        df = pd.DataFrame(filas, columns=["codigo", "deposito", "transito_bultos_pedidos"])
        if not df.empty:
            df = df.groupby(["codigo", "deposito"], as_index=False)["transito_bultos_pedidos"].sum()
        return df
