from pathlib import Path

from .base import LineaPedidoTransito, leer_pedido_generico, parse_fecha_filename

SHEET = "Subida de datos"
HEADER_ROW = 2
COL_CODIGO = 2
COL_CANTIDAD = 4  # ya viene en unidades, no hace falta UxB


def extraer(path: Path) -> list[LineaPedidoTransito]:
    fecha_fallback = parse_fecha_filename(path)
    return leer_pedido_generico(
        path=path,
        sheet=SHEET,
        header_row=HEADER_ROW,
        col_codigo=COL_CODIGO,
        col_cantidad=COL_CANTIDAD,
        col_uxb=None,
        fecha_cell=None,
        fecha_fallback=fecha_fallback,
        proveedor="La Serenisima",
    )
