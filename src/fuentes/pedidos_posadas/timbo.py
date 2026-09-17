from pathlib import Path

from .base import LineaPedidoTransito, leer_pedido_generico

SHEET = "Pedido TIMBO"
HEADER_ROW = 6
COL_CODIGO = 2
COL_ST_SEG = 3
COL_UXB = 4
COL_PEDIDO = 21
FECHA_CELL = (5, 2)


def extraer(path: Path) -> list[LineaPedidoTransito]:
    return leer_pedido_generico(
        path=path,
        sheet=SHEET,
        header_row=HEADER_ROW,
        col_codigo=COL_CODIGO,
        col_cantidad=COL_PEDIDO,
        col_uxb=COL_UXB,
        col_stock_seguridad=COL_ST_SEG,
        fecha_cell=FECHA_CELL,
        proveedor="TIMBO",
    )
