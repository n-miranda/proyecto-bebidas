"""Interfaz abstracta de fuente de datos (CLAUDE.md seccion 11).

Cambiar de Excel a SQL (futura conexion a Chess) implica escribir un adaptador
nuevo que implemente estas mismas interfaces y cambiar la instanciacion en
`consolidador.py` / `config.json` -- sin tocar el consolidador ni el calculo.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class FuenteStock(ABC):
    @abstractmethod
    def leer(self) -> pd.DataFrame:
        """Columnas: codigo (str), descripcion (str), stock_unidades (float),
        deposito (str), venta_promedio_bulto (float | None -- puede faltar).
        Un mismo codigo puede repetirse en mas de una fila si tiene stock en
        mas de un deposito."""


class FuenteVentas(ABC):
    @abstractmethod
    def leer(self) -> pd.DataFrame:
        """Columnas: codigo (str), fecha (date), unidades_vendidas (float)."""


class FuenteMaestroProductos(ABC):
    @abstractmethod
    def leer(self) -> pd.DataFrame:
        """Columnas: codigo (str), proveedor (str), unidades_por_bulto (float),
        rubro (str)."""


class FuenteTransito(ABC):
    @abstractmethod
    def leer(self) -> pd.DataFrame:
        """Columnas: codigo (str), transito_unidades (float). Se devuelve en
        unidades (igual que stock y ventas) para que la conversion a bultos
        la haga siempre el consolidador con el mismo unidades_por_bulto del
        maestro -- la fuente no decide factores de conversion por su cuenta."""

    def inconsistencias(self) -> list[dict]:
        """Inconsistencias detectadas durante la lectura (pedidos vencidos sin
        conciliar, ingresos sin pedido pendiente, etc). Lista vacia por
        defecto; las fuentes que las generan la sobreescriben."""
        return []
