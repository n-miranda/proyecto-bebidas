"""Lectura de stock desde la pestaña 'Stock' del archivo compartido de
Drive 'Stock Grupo <fecha>.xlsx' (carpeta Tablero) -- reemplaza la lectura
anterior por pestañas individuales de deposito (OB/SV/PR/TC) del archivo
manual D:\\01-Usuario\\Downloads\\stock_bebidas.xlsx.

Estructura real relevada y confirmada por el usuario (2026-10-14):
  - Hoja 'Stock': fila 1 vacia, fila 2 = encabezados reales, datos desde
    fila 3.
  - Columnas fijas: B = Codigo, D = Descripcion, G = Retiro.
  - A partir de la columna I se repite un bloque de 8 columnas por
    deposito: MA | <Deposito> Fisico | <Deposito> Disponible |
    Dias de piso | ABC | Ven Prom | Min | Max. La hoja trae 10 bloques,
    pero solo 7 son depositos operativos reales (confirmado por el
    usuario, 2026-10-14, contra la hoja 'MERCH' del mismo archivo): Obera,
    San Vicente, Puerto Rico, Virasoro, Posadas, Parana y Victoria.
    Jardin America, Apostoles y Santo Tome son columnas heredadas/vacias
    del archivo, no depositos reales -- se omiten.
  - Se usan 'Disponible', 'Ven Prom' y 'ABC'. 'Disponible' YA viene en
    BULTOS (confirmado por el usuario) -- a diferencia de la fuente
    anterior, no hay que dividir por unidades_por_bulto del maestro; el
    consolidador toma este valor directo como stock_bultos.
  - El nombre de deposito que ve la web es el del encabezado sin acentos
    (ej. 'Oberá' -> 'Obera'), a pedido del usuario (2026-10-14).
  - 'ABC' (cluster A/B/C/D del propio articulo en ese deposito, segun
    rotacion) se carga como 'cluster', vinculado por (codigo, deposito) --
    a pedido del usuario (2026-10-14), alimenta el filtro "Clúster" de la
    web, que hasta ahora no tenia datos reales.
  - 'Retiro' (columna G, un valor por articulo -- NO varia por deposito,
    a diferencia de 'ABC') se carga como 'grupo' -- a pedido del usuario
    (2026-10-14), alimenta un nuevo filtro "Grupo" en la web.

config.rutas.stock_bebidas_archivo puede apuntar a un archivo puntual o a
una carpeta (la carpeta de Drive 'Tablero', que recibe un archivo nuevo
"Stock Grupo <fecha>.xlsx" cada vez que se actualiza): si es una carpeta,
se toma el mas reciente **segun la fecha del propio nombre del archivo**
(no la fecha de modificacion del sistema de archivos) y se registra en el
log cual se uso.

IMPORTANTE (confirmado por el usuario, 2026-10-14): la fecha de
modificacion del archivo SIEMPRE queda un dia antes de la fecha que dice
el nombre -- es el flujo normal de trabajo (se prepara a la tarde/noche
para el dia siguiente), no un error de carga. Por eso tanto la eleccion
del archivo mas reciente como el aviso de "no es de hoy" se basan en la
fecha que trae el propio nombre del archivo, parseada con
_fecha_desde_nombre(). Si el nombre no trae una fecha reconocible, se cae
a la fecha de modificacion como respaldo (con un warning en el log).
"""
from __future__ import annotations

import logging
import re
from datetime import date
from pathlib import Path

import openpyxl
import pandas as pd

from src.conversion import normalizar_codigo, sin_acentos
from src.fuentes.base import FuenteStock

logger = logging.getLogger(__name__)

NOMBRE_HOJA = "STOCK"
FILA_ENCABEZADO = 2
FILA_DATOS_DESDE = 3
COL_CODIGO = 2  # B
COL_DESCRIPCION = 4  # D
COL_GRUPO = 7  # G ("Retiro" en el Excel, se muestra como "Grupo" en la web)
COL_PRIMER_BLOQUE = 9  # I (primera columna 'MA' del bloque de Obera)
ANCHO_BLOQUE = 8
CANTIDAD_BLOQUES_EN_LA_HOJA = 10  # hay 10 bloques de columnas, no todos son depositos reales
OFFSET_DISPONIBLE = 2  # dentro del bloque: MA(0) Fisico(1) Disponible(2)
OFFSET_ABC = 4  # ... Dias de piso(3) ABC(4)
OFFSET_VEN_PROM = 5  # ... Ven Prom(5)

# Depositos operativos reales (sin acentos), confirmado contra la hoja
# 'MERCH' del mismo archivo. Jardin America, Apostoles y Santo Tome
# aparecen como bloque en 'STOCK' pero siempre en cero -- no son
# depositos reales, se descartan.
DEPOSITOS_REALES = {
    "Obera", "San Vicente", "Puerto Rico", "Virasoro", "Posadas", "Parana", "Victoria",
}


# "Stock Grupo 14-10-26.xlsx" -> DD-MM-AA (dia-mes-año de 2 digitos).
PATRON_FECHA_NOMBRE = re.compile(r"(\d{1,2})-(\d{1,2})-(\d{2,4})")


def _fecha_desde_nombre(nombre_archivo: str) -> date | None:
    """Extrae la fecha DD-MM-AA del nombre ('Stock Grupo 14-10-26.xlsx' ->
    2026-10-14). None si el nombre no trae un patron de fecha reconocible
    o la fecha no es valida (ej. 32-13-26)."""
    m = PATRON_FECHA_NOMBRE.search(nombre_archivo)
    if not m:
        return None
    dia, mes, anio = (int(g) for g in m.groups())
    if anio < 100:
        anio += 2000
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def _resolver_archivo(ruta: Path) -> Path:
    if not ruta.is_dir():
        return ruta
    candidatos = list(ruta.glob("Stock Grupo*.xlsx"))
    if not candidatos:
        raise FileNotFoundError(f"No se encontro ningun 'Stock Grupo*.xlsx' en {ruta}")
    con_fecha = [(c, _fecha_desde_nombre(c.name)) for c in candidatos]
    sin_fecha_en_nombre = [c for c, f in con_fecha if f is None]
    if sin_fecha_en_nombre:
        logger.warning(
            "STOCK: %d archivo(s) sin fecha reconocible en el nombre, se ordenan por "
            "fecha de modificacion como respaldo: %s",
            len(sin_fecha_en_nombre), [c.name for c in sin_fecha_en_nombre],
        )
    # Se prioriza la fecha del nombre (mas confiable segun el usuario -- la
    # fecha de modificacion del archivo siempre queda un dia antes, porque se
    # prepara la tarde anterior); fecha de modificacion solo como desempate o
    # respaldo para archivos sin fecha reconocible en el nombre.
    elegido, fecha_nombre = max(
        con_fecha, key=lambda par: (par[1] or date.min, par[0].stat().st_mtime)
    )
    logger.info(
        "STOCK: carpeta=%s -> archivo elegido=%s (fecha del nombre=%s)",
        ruta, elegido.name, fecha_nombre.isoformat() if fecha_nombre else "sin fecha, se uso mtime",
    )
    return elegido


def _detectar_depositos(encabezados: tuple) -> list[tuple[str, int, int, int]]:
    """Devuelve (nombre_deposito_sin_acentos, idx_disponible_0based,
    idx_abc_0based, idx_ven_prom_0based) por cada bloque de deposito
    detectado."""
    depositos = []
    for i in range(CANTIDAD_BLOQUES_EN_LA_HOJA):
        col_inicio = COL_PRIMER_BLOQUE + i * ANCHO_BLOQUE  # 1-based
        idx_disponible = col_inicio + OFFSET_DISPONIBLE - 1  # 0-based
        idx_abc = col_inicio + OFFSET_ABC - 1
        idx_ven_prom = col_inicio + OFFSET_VEN_PROM - 1
        header = encabezados[idx_disponible] if idx_disponible < len(encabezados) else None
        if not header or "disponible" not in str(header).lower():
            logger.warning(
                "STOCK: columna 'Disponible' esperada en indice %d no coincide (header=%r), se omite ese bloque",
                idx_disponible, header,
            )
            continue
        nombre = sin_acentos(str(header).replace("Disponible", "").strip())
        if nombre not in DEPOSITOS_REALES:
            logger.info(
                "STOCK: bloque '%s' (indice %d) no es un deposito real, se omite", nombre, idx_disponible,
            )
            continue
        depositos.append((nombre, idx_disponible, idx_abc, idx_ven_prom))
    return depositos


class ExcelStock(FuenteStock):
    def __init__(self, archivo: Path):
        self.archivo = archivo
        # Se completa en leer(): que archivo se termino usando (el nombre
        # cambia dia a dia, ver _resolver_archivo) y su fecha de
        # modificacion, para que el consolidador pueda avisar si el stock
        # mostrado no es de hoy (a pedido del usuario, 2026-10-14: nadie
        # garantiza que se suba un 'Stock Grupo' nuevo todos los dias).
        self.archivo_usado: Path | None = None
        self.fecha_archivo_usado: date | None = None

    def leer(self) -> pd.DataFrame:
        archivo = _resolver_archivo(self.archivo)
        if not archivo.exists():
            raise FileNotFoundError(f"No se encontro el archivo de stock: {archivo}")
        self.archivo_usado = archivo
        # Fecha del propio nombre del archivo, no de modificacion del
        # sistema de archivos -- ver nota en el docstring del modulo.
        self.fecha_archivo_usado = _fecha_desde_nombre(archivo.name) or date.fromtimestamp(archivo.stat().st_mtime)
        wb = openpyxl.load_workbook(archivo, data_only=True, read_only=True)
        nombre_hoja = next((h for h in wb.sheetnames if h.strip().upper() == NOMBRE_HOJA), None)
        if nombre_hoja is None:
            raise FileNotFoundError(f"El archivo {archivo.name} no tiene la pestaña '{NOMBRE_HOJA}'")
        ws = wb[nombre_hoja]

        encabezados = next(
            ws.iter_rows(min_row=FILA_ENCABEZADO, max_row=FILA_ENCABEZADO, values_only=True)
        )
        depositos = _detectar_depositos(encabezados)
        if not depositos:
            raise FileNotFoundError(
                f"No se encontraron columnas 'Disponible' por deposito en la pestaña "
                f"'{NOMBRE_HOJA}' de {archivo.name}"
            )

        filas = []
        for fila in ws.iter_rows(min_row=FILA_DATOS_DESDE, values_only=True):
            codigo_raw = fila[COL_CODIGO - 1] if len(fila) >= COL_CODIGO else None
            if codigo_raw is None:
                continue
            codigo = normalizar_codigo(codigo_raw)
            descripcion = fila[COL_DESCRIPCION - 1] if len(fila) >= COL_DESCRIPCION else None
            descripcion = descripcion.strip() if isinstance(descripcion, str) else descripcion
            grupo_raw = fila[COL_GRUPO - 1] if len(fila) >= COL_GRUPO else None
            grupo = str(grupo_raw).strip() if isinstance(grupo_raw, str) and grupo_raw.strip() else None
            for nombre_deposito, idx_disponible, idx_abc, idx_ven_prom in depositos:
                disponible = fila[idx_disponible] if idx_disponible < len(fila) else None
                if disponible is None:
                    continue
                try:
                    stock_bultos = float(disponible)
                except (TypeError, ValueError):
                    continue
                ven_prom = fila[idx_ven_prom] if idx_ven_prom < len(fila) else None
                try:
                    venta_promedio_bulto = float(ven_prom) if ven_prom is not None else None
                except (TypeError, ValueError):
                    venta_promedio_bulto = None
                abc = fila[idx_abc] if idx_abc < len(fila) else None
                cluster = str(abc).strip() if isinstance(abc, str) and abc.strip() else None
                filas.append({
                    "codigo": codigo,
                    "descripcion": descripcion,
                    "stock_bultos": stock_bultos,
                    "deposito": nombre_deposito,
                    "venta_promedio_bulto": venta_promedio_bulto,
                    "cluster": cluster,
                    "grupo": grupo,
                })
        wb.close()

        df = pd.DataFrame(
            filas,
            columns=["codigo", "descripcion", "stock_bultos", "deposito", "venta_promedio_bulto", "cluster", "grupo"],
        )
        logger.info(
            "STOCK: archivo=%s filas_totales=%d codigos_unicos=%d depositos=%s",
            archivo.name, len(df),
            df["codigo"].nunique() if not df.empty else 0,
            sorted(df["deposito"].unique()) if not df.empty else [],
        )
        return df
