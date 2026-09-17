"""Lectura de VENTAS\\*.xlsx (CLAUDE.md seccion 4.2).

Estructura real relevada (Paso 0): columna A = fecha (ya viene como
datetime, no hace falta deducirla del nombre de archivo), B = codigo,
C = descripcion, D = unidades vendidas (con signo: negativas = devoluciones/
notas de credito, se restan sin descartar).

Se leen TODOS los archivos .xlsx de la carpeta y se descartan duplicados por
(archivo, fila) -- relevante si en el futuro vuelven a repartir las ventas
en un archivo por dia y el mismo dia aparece en dos archivos.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

import openpyxl
import pandas as pd

from src.conversion import normalizar_codigo
from src.fuentes.base import FuenteVentas

logger = logging.getLogger(__name__)


class ExcelVentas(FuenteVentas):
    def __init__(self, carpeta: Path):
        self.carpeta = carpeta

    def leer(self) -> pd.DataFrame:
        if not self.carpeta.exists():
            raise FileNotFoundError(f"No existe la carpeta de VENTAS: {self.carpeta}")
        archivos = sorted(p for p in self.carpeta.glob("*.xlsx") if not p.name.startswith("~$"))
        if not archivos:
            raise FileNotFoundError(f"No hay archivos de ventas en {self.carpeta}")

        marcas_vistas: set[tuple[str, int]] = set()
        filas = []
        for archivo in archivos:
            wb = openpyxl.load_workbook(archivo, data_only=True, read_only=True)
            ws = wb[wb.sheetnames[0]]
            leidas = 0
            duplicadas = 0
            for num_fila, row in enumerate(
                ws.iter_rows(min_row=2, max_col=4, values_only=True), start=2
            ):
                fecha_raw, codigo_raw, _descripcion, unidades = row
                if codigo_raw is None or fecha_raw is None:
                    continue
                marca = (archivo.name, num_fila)
                if marca in marcas_vistas:
                    duplicadas += 1
                    continue
                marcas_vistas.add(marca)

                if isinstance(fecha_raw, datetime):
                    fecha = fecha_raw.date()
                elif isinstance(fecha_raw, date):
                    fecha = fecha_raw
                else:
                    fecha = pd.to_datetime(fecha_raw).date()

                filas.append({
                    "codigo": normalizar_codigo(codigo_raw),
                    "fecha": fecha,
                    "unidades_vendidas": float(unidades) if unidades is not None else 0.0,
                })
                leidas += 1
            wb.close()
            logger.info(
                "VENTAS: archivo=%s filas_leidas=%d duplicadas_descartadas=%d",
                archivo.name, leidas, duplicadas,
            )

        df = pd.DataFrame(filas, columns=["codigo", "fecha", "unidades_vendidas"])
        logger.info(
            "VENTAS: total filas=%d, archivos=%d, rango fechas=%s a %s",
            len(df), len(archivos),
            df["fecha"].min() if not df.empty else "-",
            df["fecha"].max() if not df.empty else "-",
        )
        return df
