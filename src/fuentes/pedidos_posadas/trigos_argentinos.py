from pathlib import Path

from .base import LineaPedidoTransito, leer_pedido_generico

# El archivo real es una planilla de reposicion multi-hoja. La cantidad a
# pedir esta en la hoja "Pedido Salteña" -- rotulada internamente "La
# Salteña" pese a contener productos YULI/PIPORINO (marca real: Trigos
# Argentinos; rotulo de plantilla reciclada, no confundir con el proveedor
# La Salteña, que no se procesa en este proyecto).
SHEET = "Pedido Salteña"
HEADER_ROW = 6
COL_CODIGO = 1
COL_ST_SEG = 2
COL_UXB = 3
COL_PEDIDO = 20
FECHA_CELL = (5, 1)


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
        proveedor="TRIGOS ARGENTINOS",
    )
