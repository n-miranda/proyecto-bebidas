"""Carga y valida config.json. Ninguna ruta ni regla de negocio va hardcodeada
en el resto del codigo: todo sale de aca."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
CONFIG_JSON = RAIZ_PROYECTO / "config" / "config.json"


class ConfigError(Exception):
    """Error de configuracion con mensaje claro en castellano para el usuario."""


@dataclass(frozen=True)
class Rutas:
    stock_carpeta: Path
    stock_archivo: str
    rubros_archivo: str
    stock_bebidas_archivo: Path
    ventas_carpeta: Path
    transito_carpeta: Path
    ingresos_archivo: str
    supply_pedidos_carpeta: Path
    maestro_productos: Path
    salida: Path
    logs: Path


@dataclass(frozen=True)
class Calculo:
    ventana_dias_venta: int
    incluir_dia_actual: bool
    contar_dias_turisticos: bool
    redondeo_decimales: int


@dataclass(frozen=True)
class SemaforoDiasStock:
    rojo_hasta: float
    amarillo_hasta: float
    verde_hasta: float


@dataclass(frozen=True)
class Transito:
    dias_vencimiento_pendiente: int


@dataclass(frozen=True)
class SemaforoRelativoStockSeguridad:
    amarillo_hasta_multiplo: float
    verde_hasta_multiplo: float


@dataclass(frozen=True)
class Config:
    rutas: Rutas
    calculo: Calculo
    semaforo_dias_stock: SemaforoDiasStock
    semaforo_relativo_stock_seguridad: SemaforoRelativoStockSeguridad
    transito: Transito
    proveedores_excluidos: tuple[str, ...]


def _resolver_ruta(valor: str) -> Path:
    """Rutas absolutas (con o sin drive) se respetan tal cual; las relativas
    se resuelven contra la raiz del proyecto."""
    p = Path(valor)
    if p.is_absolute():
        return p
    return RAIZ_PROYECTO / p


def cargar_config(ruta: Path = CONFIG_JSON) -> Config:
    if not ruta.exists():
        raise ConfigError(
            f"No se encontro el archivo de configuracion: {ruta}. "
            "Sin ese archivo la aplicacion no sabe donde buscar los datos."
        )
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"El archivo {ruta} tiene un JSON invalido: {exc}") from exc

    try:
        r = datos["rutas"]
        c = datos["calculo"]
        s = datos["semaforo_dias_stock"]
        t = datos["transito"]
        sr = datos["semaforo_relativo_stock_seguridad"]
    except KeyError as exc:
        raise ConfigError(f"Falta la seccion {exc} en {ruta}") from exc

    rutas = Rutas(
        stock_carpeta=_resolver_ruta(r["stock_carpeta"]),
        stock_archivo=r["stock_archivo"],
        rubros_archivo=r["rubros_archivo"],
        stock_bebidas_archivo=_resolver_ruta(r["stock_bebidas_archivo"]),
        ventas_carpeta=_resolver_ruta(r["ventas_carpeta"]),
        transito_carpeta=_resolver_ruta(r["transito_carpeta"]),
        ingresos_archivo=r["ingresos_archivo"],
        supply_pedidos_carpeta=_resolver_ruta(r["supply_pedidos_carpeta"]),
        maestro_productos=_resolver_ruta(r["maestro_productos"]),
        salida=_resolver_ruta(r["salida"]),
        logs=_resolver_ruta(r["logs"]),
    )
    calculo = Calculo(
        ventana_dias_venta=int(c["ventana_dias_venta"]),
        incluir_dia_actual=bool(c["incluir_dia_actual"]),
        contar_dias_turisticos=bool(c["contar_dias_turisticos"]),
        redondeo_decimales=int(c["redondeo_decimales"]),
    )
    semaforo = SemaforoDiasStock(
        rojo_hasta=float(s["rojo_hasta"]),
        amarillo_hasta=float(s["amarillo_hasta"]),
        verde_hasta=float(s["verde_hasta"]),
    )
    transito = Transito(
        dias_vencimiento_pendiente=int(t["dias_vencimiento_pendiente"]),
    )
    semaforo_relativo = SemaforoRelativoStockSeguridad(
        amarillo_hasta_multiplo=float(sr["amarillo_hasta_multiplo"]),
        verde_hasta_multiplo=float(sr["verde_hasta_multiplo"]),
    )
    proveedores_excluidos = tuple(datos.get("proveedores_excluidos", {}).get("lista", []))
    return Config(
        rutas=rutas, calculo=calculo, semaforo_dias_stock=semaforo,
        semaforo_relativo_stock_seguridad=semaforo_relativo, transito=transito,
        proveedores_excluidos=proveedores_excluidos,
    )
