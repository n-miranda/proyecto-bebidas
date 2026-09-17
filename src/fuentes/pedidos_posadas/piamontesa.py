from pathlib import Path

from .base import LineaPedidoTransito, leer_pedido_generico

SHEET = "PEDIDO"
HEADER_ROW = 12
COL_CODIGO = 2
COL_D_ST = 3  # "D St": a diferencia de otros proveedores, varia por producto (no es un fijo por proveedor)
COL_UXB = 4
COL_PEDIDO = 22  # 'Columna1': confirmado via la formula real de Cargar Pedido -> Cantidad solicitada
FECHA_CELL = (8, 2)


def extraer(path: Path) -> list[LineaPedidoTransito]:
    return leer_pedido_generico(
        path=path,
        sheet=SHEET,
        header_row=HEADER_ROW,
        col_codigo=COL_CODIGO,
        col_cantidad=COL_PEDIDO,
        col_uxb=COL_UXB,
        col_stock_seguridad=COL_D_ST,
        fecha_cell=FECHA_CELL,
        proveedor="Piamontesa",
    )
