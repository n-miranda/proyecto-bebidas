"""Lectura de los pedidos pendientes por empresa en la carpeta de Drive
'Tablero' (ej. '1. 1994 - Pedidos.xlsx', '2. Total Center - Pedidos.xlsx',
'4. Kerá Guazú - Pedidos.xlsx') -- reemplaza la lectura anterior de
TRANSITO\\<OB/SV/PR/TC> - Pedidos.xlsx (agregado 2026-09-19), que usaba
codigos de 2 letras que dejaron de existir cuando el stock paso a nombres
completos de deposito (ver excel_stock.py, 2026-10-14).

A diferencia de la fuente anterior, el deposito NO sale del nombre del
archivo (cada archivo es por EMPRESA, no por deposito: una empresa puede
cubrir varios depositos -- ver CRUCE-depositos.jpeg, cruce Deposito<->
Empresa confirmado por el usuario 2026-10-14) sino de la propia fila,
columna 'Depósito' de la pestaña 'Base'. Se filtra contra la misma lista
blanca de 7 depositos reales que usa excel_stock.py (DEPOSITOS_REALES).

Pestaña "Base" (busqueda case-insensitive del nombre): columnas por
posicion D=Remito, G=Depósito, I=Cod., Q=Pedido a retirar (K=Pedido
Original (Bultos) como respaldo si Q viene vacia -- Q ya descuenta Baja/
Agregado/Ajuste CMQ, es la cantidad real pendiente, mas precisa que K).
Un pedido sin remito todavia (columna D vacia) esta pendiente de recibir.
Si el remito ya tiene numero, el pedido ya se desapcho/facturo y no cuenta
como transito pendiente (se omite, tal como pidio el usuario en la fuente
anterior).

NOTA: al 2026-10-14 no existe en la carpeta 'Tablero' un archivo de
pedidos para 'Total Litoral S.A.' (la empresa de Paraná y Victoria segun
CRUCE-depositos.jpeg) -- esos dos depositos quedan sin transito hasta que
aparezca ese archivo. No es un error: la app sigue funcionando con
transito=0 para ellos."""
from __future__ import annotations

import logging
from pathlib import Path

import openpyxl
import pandas as pd

from src.conversion import normalizar_codigo, sin_acentos
from src.fuentes.excel_stock import DEPOSITOS_REALES

logger = logging.getLogger(__name__)

COL_REMITO = 3  # D (0-based)
COL_DEPOSITO = 6  # G
COL_CODIGO = 8  # I
COL_PEDIDO_ORIGINAL = 10  # K
COL_PEDIDO_A_RETIRAR = 16  # Q


class TransitoPedidosDeposito:
    def __init__(self, carpeta: Path):
        self.carpeta = carpeta

    def _archivos(self) -> list[Path]:
        if not self.carpeta.exists():
            return []
        return sorted(
            a for a in self.carpeta.glob("*.xlsx")
            if not a.name.startswith("~$") and "pedidos" in a.stem.lower()
        )

    def leer(self) -> pd.DataFrame:
        filas = []
        for archivo in self._archivos():
            wb = openpyxl.load_workbook(archivo, data_only=True, read_only=True)
            nombre_hoja = next((h for h in wb.sheetnames if h.strip().lower() == "base"), None)
            if nombre_hoja is None:
                logger.warning("PEDIDOS: %s no tiene pestaña 'Base', se omite", archivo.name)
                wb.close()
                continue
            ws = wb[nombre_hoja]
            leidas = 0
            pendientes = 0
            depositos_desconocidos = set()
            for fila in ws.iter_rows(min_row=2, max_col=COL_PEDIDO_A_RETIRAR + 1, values_only=True):
                codigo_raw = fila[COL_CODIGO] if len(fila) > COL_CODIGO else None
                if codigo_raw is None:
                    continue
                leidas += 1
                deposito_raw = fila[COL_DEPOSITO] if len(fila) > COL_DEPOSITO else None
                if not deposito_raw:
                    continue
                deposito = sin_acentos(str(deposito_raw).strip())
                if deposito not in DEPOSITOS_REALES:
                    depositos_desconocidos.add(deposito)
                    continue
                remito = fila[COL_REMITO] if len(fila) > COL_REMITO else None
                if remito is not None and str(remito).strip() != "":
                    continue  # ya tiene remito -> ya se despacho, no es transito pendiente
                cantidad = fila[COL_PEDIDO_A_RETIRAR] if len(fila) > COL_PEDIDO_A_RETIRAR else None
                if cantidad is None:
                    cantidad = fila[COL_PEDIDO_ORIGINAL] if len(fila) > COL_PEDIDO_ORIGINAL else None
                if cantidad is None:
                    continue
                try:
                    cantidad = float(cantidad)
                except (TypeError, ValueError):
                    continue
                filas.append({
                    "codigo": normalizar_codigo(codigo_raw),
                    "deposito": deposito,
                    "transito_bultos_pedidos": cantidad,
                })
                pendientes += 1
            wb.close()
            if depositos_desconocidos:
                logger.info(
                    "PEDIDOS: archivo=%s depositos ajenos a la lista de 7 reales, se omiten: %s",
                    archivo.name, sorted(depositos_desconocidos),
                )
            logger.info(
                "PEDIDOS: archivo=%s filas=%d pendientes_sin_remito=%d",
                archivo.name, leidas, pendientes,
            )

        df = pd.DataFrame(filas, columns=["codigo", "deposito", "transito_bultos_pedidos"])
        if not df.empty:
            df = df.groupby(["codigo", "deposito"], as_index=False)["transito_bultos_pedidos"].sum()
        return df
