"""Dias de venta, feriados y ventana de 7 dias (CLAUDE.md seccion 5.1 y 5.2).

Un dia es dia de venta si NO es domingo ni feriado nacional (inamovible o
trasladable). Los feriados turisticos cuentan como dia de venta salvo que
`contar_dias_turisticos=False` en config.json.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
FERIADOS_JSON = RAIZ_PROYECTO / "config" / "feriados.json"


class CalendarioError(Exception):
    """Error de calendario con mensaje claro en castellano para el usuario."""


class Feriados:
    """Feriados de un anio, cargados desde config/feriados.json."""

    def __init__(self, anio: int, inamovibles: set[date], trasladables: set[date], turisticos: set[date]):
        self.anio = anio
        self.inamovibles = inamovibles
        self.trasladables = trasladables
        self.turisticos = turisticos

    @property
    def no_laborables(self) -> set[date]:
        return self.inamovibles | self.trasladables


def _parsear_fechas(valores: list[str]) -> set[date]:
    return {date.fromisoformat(v) for v in valores}


def cargar_feriados(anio: int, ruta: Path = FERIADOS_JSON) -> Feriados:
    if not ruta.exists():
        raise CalendarioError(f"No se encontro el archivo de feriados: {ruta}")
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CalendarioError(f"El archivo {ruta} tiene un JSON invalido: {exc}") from exc

    clave = str(anio)
    if clave not in datos:
        raise CalendarioError(
            f"El anio {anio} no esta cargado en {ruta}. "
            "Agregar sus feriados antes de calcular sobre ese anio; "
            "no se asume que un anio sin datos no tiene feriados."
        )

    bloque = datos[clave]
    try:
        return Feriados(
            anio=anio,
            inamovibles=_parsear_fechas(bloque["inamovibles"]),
            trasladables=_parsear_fechas(bloque["trasladables"]),
            turisticos=_parsear_fechas(bloque["turisticos"]),
        )
    except KeyError as exc:
        raise CalendarioError(f"Falta la clave {exc} en el bloque {clave} de {ruta}") from exc


def _feriados_para(fecha: date, cache: dict[int, Feriados]) -> Feriados:
    if fecha.year not in cache:
        cache[fecha.year] = cargar_feriados(fecha.year)
    return cache[fecha.year]


def es_dia_de_venta(fecha: date, feriados: Feriados, contar_dias_turisticos: bool = True) -> bool:
    """Domingo -> no. Feriado inamovible/trasladable -> no. Turistico -> no
    solo si contar_dias_turisticos=False. Sabado -> si cuenta."""
    if fecha.weekday() == 6:  # lunes=0 ... domingo=6
        return False
    if fecha in feriados.no_laborables:
        return False
    if not contar_dias_turisticos and fecha in feriados.turisticos:
        return False
    return True


def ventana_dias_venta(
    fecha_referencia: date,
    n: int = 7,
    incluir_dia_actual: bool = True,
    contar_dias_turisticos: bool = True,
) -> list[date]:
    """Devuelve los ultimos `n` dias de venta contando hacia atras desde
    `fecha_referencia`, de mas antiguo a mas reciente."""
    cache: dict[int, Feriados] = {}
    dias: list[date] = []
    d = fecha_referencia if incluir_dia_actual else fecha_referencia - timedelta(days=1)
    # limite de seguridad: nunca deberia hacer falta retroceder mas de ~60
    # dias corridos para juntar 7 dias de venta.
    limite = fecha_referencia - timedelta(days=60)
    while len(dias) < n:
        if d < limite:
            raise CalendarioError(
                f"No se pudieron juntar {n} dias de venta retrocediendo desde "
                f"{fecha_referencia.isoformat()}; revisar feriados.json."
            )
        feriados = _feriados_para(d, cache)
        if es_dia_de_venta(d, feriados, contar_dias_turisticos):
            dias.append(d)
        d -= timedelta(days=1)
    dias.reverse()
    return dias
