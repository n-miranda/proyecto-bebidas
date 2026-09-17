"""Normalizacion de codigo, conversion unidades<->bultos y calculo de dias de
stock (CLAUDE.md secciones 4.5, 5.3, 5.4)."""
from __future__ import annotations


def normalizar_codigo(valor) -> str:
    """Clave unica de cruce: siempre string, sin espacios, sin decimales
    espurios (Excel a veces trae el codigo como float), sin ceros a la
    izquierda perdidos porque el codigo fuente ya es numerico puro en las
    4 fuentes relevadas (stock, rubros, ventas, maestro de productos)."""
    if valor is None:
        raise ValueError("codigo vacio: no se puede normalizar")
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    texto = str(valor).strip()
    if texto == "":
        raise ValueError("codigo vacio: no se puede normalizar")
    return texto


def convertir_a_bultos(unidades: float, unidades_por_bulto: float) -> float:
    """unidades_por_bulto nunca puede ser 0: si lo es o falta, tratar como 1."""
    upb = unidades_por_bulto if unidades_por_bulto else 1
    return unidades / upb


def calcular_dias_stock(stock_bultos: float, promedio_diario_bultos: float) -> float | None:
    """Tabla de casos borde (CLAUDE.md 5.4). Nunca divide por cero ni
    devuelve inf."""
    if promedio_diario_bultos == 0:
        return None
    if stock_bultos <= 0:
        return 0.0
    return stock_bultos / promedio_diario_bultos


def clasificar_riesgo(
    dias_stock: float | None,
    dias_stock_seguridad: float | None,
    rojo_hasta: float,
    amarillo_hasta: float,
    verde_hasta: float,
    multiplo_amarillo: float,
    multiplo_verde: float,
) -> str:
    """Color de riesgo por articulo (nunca se manda 'dias_stock_seguridad' a
    la web, solo el resultado). Si el producto tiene un piso de stock de
    seguridad propio (St Seg / D St, sacado de sus pedidos reales), ese piso
    reemplaza al umbral fijo global: rojo por debajo del piso, amarillo hasta
    `multiplo_amarillo` veces el piso, verde hasta `multiplo_verde` veces.
    Sin piso conocido, se usan los umbrales fijos de config.json (igual que
    antes). 'neutro' = sin venta, no se puede clasificar (S/V o -)."""
    if dias_stock is None:
        return "neutro"

    if dias_stock_seguridad:
        limite_rojo = dias_stock_seguridad
        limite_amarillo = dias_stock_seguridad * multiplo_amarillo
        limite_verde = dias_stock_seguridad * multiplo_verde
    else:
        limite_rojo = rojo_hasta
        limite_amarillo = amarillo_hasta
        limite_verde = verde_hasta

    if dias_stock < limite_rojo:
        return "rojo"
    if dias_stock < limite_amarillo:
        return "amarillo"
    if dias_stock < limite_verde:
        return "verde"
    return "sobrestock"
