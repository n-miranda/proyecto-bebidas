"""Transito (CLAUDE.md seccion 4.4, cerrado en sesion del 2026-09-08).

Dos fuentes independientes, ninguna requiere interaccion del usuario en la
web (la web es de solo lectura):

- ENTRADA (pedidos generados): se recorren las carpetas de proveedor dentro
  de `supply_pedidos_carpeta` (solo el nivel superior, sin subcarpetas -- ahi
  viven los pedidos ya resueltos/archivados), tomando siempre el archivo mas
  reciente por fecha de modificacion. Reutiliza los extractores de
  `fuentes/pedidos_posadas/` (columnas ya validadas contra archivos reales en
  AUTOMATIZACION_PEDIDOS_CONTROL). Cada pedido nuevo detectado (por hash del
  archivo, para no reprocesar) se suma a lo pendiente.
- SALIDA (confirmacion de llegada): `INGRESOS.xlsx`, planilla acumulativa que
  arma el usuario a mano desde Chess (nunca se borra, solo se agregan filas
  al final). Se detectan filas nuevas por posicion (cuantas filas tenia la
  ultima vez), y cada ingreso nuevo resta cantidad contra lo pendiente del
  mismo codigo: primero contra el pendiente cuya fecha_pedido coincide exacto
  con la columna PEDIDO del ingreso: si no hay coincidencia exacta, se usa el
  pendiente mas antiguo de ese codigo (FIFO) como respaldo.

Ambos lados persisten su estado en `salida\\` para no reprocesar nada en cada
corrida (mismo criterio de idempotencia que el resto del proyecto).
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import openpyxl
import pandas as pd

from src.conversion import normalizar_codigo
from src.fuentes.base import FuenteTransito
from src.fuentes.pedidos_posadas import EXTRACTORES

logger = logging.getLogger(__name__)


@dataclass
class PedidoPendiente:
    codigo: str
    proveedor: str
    cantidad_pedida: float
    cantidad_pendiente: float
    fecha_pedido: str  # ISO (date)
    archivo_origen: str


def _hash_archivo(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TransitoSupplyIngresos(FuenteTransito):
    def __init__(
        self,
        supply_pedidos_carpeta: Path,
        ingresos_archivo: Path,
        estado_carpeta: Path,
        dias_vencimiento: int = 30,
    ):
        self.supply_pedidos_carpeta = supply_pedidos_carpeta
        self.ingresos_archivo = ingresos_archivo
        self.ruta_pendientes = estado_carpeta / "transito_pendientes.json"
        self.ruta_registro_pedidos = estado_carpeta / "transito_registro_pedidos.json"
        self.ruta_registro_ingresos = estado_carpeta / "transito_registro_ingresos.json"
        self.ruta_excedentes = estado_carpeta / "transito_excedentes_sin_match.json"
        self.ruta_politica = estado_carpeta / "politica_dias_stock.json"
        self.dias_vencimiento = dias_vencimiento
        self._inconsistencias: list[dict] = []

    # ---------- persistencia ----------

    def _cargar_json(self, ruta: Path, default):
        if not ruta.exists():
            return default
        return json.loads(ruta.read_text(encoding="utf-8"))

    def _guardar_json(self, ruta: Path, datos) -> None:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- entrada: pedidos nuevos ----------

    def _detectar_pedidos_nuevos(self, pendientes: list[PedidoPendiente]) -> list[PedidoPendiente]:
        registro = self._cargar_json(self.ruta_registro_pedidos, {})
        politica = self._cargar_json(self.ruta_politica, {})
        if not self.supply_pedidos_carpeta.exists():
            self._inconsistencias.append({
                "codigo": "-", "descripcion": "-",
                "motivo": f"No existe la carpeta de pedidos: {self.supply_pedidos_carpeta}",
            })
            return pendientes

        for proveedor, extraer in EXTRACTORES.items():
            carpeta = self.supply_pedidos_carpeta / proveedor
            if not carpeta.exists():
                continue
            candidatos = [
                p for p in carpeta.iterdir()
                if p.is_file() and not p.name.startswith("~$") and p.suffix.lower() in (".xlsx", ".xls")
            ]
            if not candidatos:
                continue
            mas_reciente = max(candidatos, key=lambda p: p.stat().st_mtime)

            hash_actual = _hash_archivo(mas_reciente)
            info_previa = registro.get(proveedor, {})
            if info_previa.get("hash") == hash_actual:
                continue  # mismo archivo que la ultima vez, nada nuevo

            try:
                lineas = extraer(mas_reciente)
            except Exception as exc:  # noqa: BLE001 - error esperable de formato de archivo
                self._inconsistencias.append({
                    "codigo": "-", "descripcion": proveedor,
                    "motivo": f"No se pudo leer el pedido '{mas_reciente.name}': {exc}",
                })
                continue

            for linea in lineas:
                pendientes.append(PedidoPendiente(
                    codigo=linea.codigo,
                    proveedor=linea.proveedor,
                    cantidad_pedida=linea.cantidad_unidades,
                    cantidad_pendiente=linea.cantidad_unidades,
                    fecha_pedido=linea.fecha_pedido.isoformat(),
                    archivo_origen=linea.archivo_origen,
                ))
                # Politica de riesgo por producto (St Seg / D St): se
                # actualiza con el ultimo pedido visto de cada codigo, sin
                # importar si ese pedido ya se concilio o no en transito.
                # Nunca se muestra en la web -- solo define el color.
                if linea.dias_stock_seguridad is not None:
                    politica[linea.codigo] = {
                        "dias_stock_seguridad": linea.dias_stock_seguridad,
                        "proveedor": linea.proveedor,
                        "fecha_pedido": linea.fecha_pedido.isoformat(),
                    }
            logger.info(
                "TRANSITO entrada: %s -> %s, %d lineas nuevas en transito",
                proveedor, mas_reciente.name, len(lineas),
            )
            registro[proveedor] = {"archivo": mas_reciente.name, "hash": hash_actual}

        self._guardar_json(self.ruta_registro_pedidos, registro)
        self._guardar_json(self.ruta_politica, politica)
        return pendientes

    def leer_politica_dias_stock(self) -> dict[str, float]:
        """codigo -> dias_stock_seguridad (piso minimo de cobertura segun el
        ultimo pedido leido de ese producto). Solo cubre los codigos que
        aparecieron en algun pedido de un proveedor cuyo archivo trae esa
        columna (todos menos La Serenisima); el resto usa el umbral fijo
        global como respaldo."""
        politica = self._cargar_json(self.ruta_politica, {})
        return {codigo: datos["dias_stock_seguridad"] for codigo, datos in politica.items()}

    # ---------- salida: ingresos ----------

    def _aplicar_ingresos_nuevos(self, pendientes: list[PedidoPendiente]) -> list[PedidoPendiente]:
        if not self.ingresos_archivo.exists():
            self._inconsistencias.append({
                "codigo": "-", "descripcion": "-",
                "motivo": f"No existe el archivo de ingresos: {self.ingresos_archivo}",
            })
            return pendientes

        registro = self._cargar_json(self.ruta_registro_ingresos, {"filas_procesadas": 0})
        filas_ya_vistas = registro.get("filas_procesadas", 0)
        excedentes = self._cargar_json(self.ruta_excedentes, [])

        wb = openpyxl.load_workbook(self.ingresos_archivo, data_only=True, read_only=True)
        ws = wb["INGRESOS"]
        total_filas_datos = ws.max_row - 1  # sin contar encabezado

        if total_filas_datos <= filas_ya_vistas:
            wb.close()
            return pendientes  # nada nuevo desde la ultima corrida

        fila_inicio = filas_ya_vistas + 2  # +1 encabezado, +1 primera fila nueva
        filas_iteradas = 0
        for row in ws.iter_rows(min_row=fila_inicio, max_row=ws.max_row, max_col=5, values_only=True):
            filas_iteradas += 1
            codigo_raw, descripcion, cantidad_raw, fecha_ingreso_raw, fecha_pedido_raw = row
            if codigo_raw is None or cantidad_raw in (None, "", " "):
                continue
            codigo = normalizar_codigo(codigo_raw)
            cantidad = float(cantidad_raw)
            fecha_pedido = fecha_pedido_raw.date().isoformat() if isinstance(fecha_pedido_raw, datetime) else None

            candidatos = [p for p in pendientes if p.codigo == codigo and p.cantidad_pendiente > 0]
            if fecha_pedido:
                exactos = [p for p in candidatos if p.fecha_pedido == fecha_pedido]
                candidatos = exactos if exactos else candidatos
            candidatos.sort(key=lambda p: p.fecha_pedido)  # FIFO: mas antiguo primero

            restante = cantidad
            for pendiente in candidatos:
                if restante <= 0:
                    break
                aplicado = min(pendiente.cantidad_pendiente, restante)
                pendiente.cantidad_pendiente -= aplicado
                restante -= aplicado

            if restante > 0:
                excedentes.append({
                    "codigo": codigo, "descripcion": descripcion,
                    "motivo": (
                        f"Ingreso de {cantidad:g} unidades sin pedido pendiente que lo explique "
                        f"({restante:g} unidades sin match, detectado el {date.today().isoformat()})"
                    ),
                })

        wb.close()
        pendientes = [p for p in pendientes if p.cantidad_pendiente > 0]
        registro["filas_procesadas"] = filas_ya_vistas + filas_iteradas
        self._guardar_json(self.ruta_registro_ingresos, registro)
        self._guardar_json(self.ruta_excedentes, excedentes)
        logger.info("TRANSITO salida: %d filas de ingresos nuevas procesadas", filas_iteradas)
        return pendientes

    # ---------- vencimiento ----------

    def _marcar_vencidos(self, pendientes: list[PedidoPendiente]) -> None:
        limite = date.today() - timedelta(days=self.dias_vencimiento)
        for p in pendientes:
            if date.fromisoformat(p.fecha_pedido) < limite:
                self._inconsistencias.append({
                    "codigo": p.codigo, "descripcion": p.proveedor,
                    "motivo": (
                        f"Pedido del {p.fecha_pedido} sigue pendiente hace mas de "
                        f"{self.dias_vencimiento} dias sin conciliarse contra ingresos"
                    ),
                })

    # ---------- interfaz FuenteTransito ----------

    def leer(self) -> pd.DataFrame:
        self._inconsistencias = []
        datos_previos = self._cargar_json(self.ruta_pendientes, [])
        pendientes = [PedidoPendiente(**d) for d in datos_previos]

        pendientes = self._detectar_pedidos_nuevos(pendientes)
        pendientes = self._aplicar_ingresos_nuevos(pendientes)
        self._marcar_vencidos(pendientes)

        self._guardar_json(self.ruta_pendientes, [asdict(p) for p in pendientes])

        # Los excedentes sin match quedan persistidos (no solo en la corrida
        # que los detecto) para que no desaparezcan del reporte hasta que
        # alguien los resuelva a mano en INGRESOS.xlsx o en el pedido.
        self._inconsistencias.extend(self._cargar_json(self.ruta_excedentes, []))

        if not pendientes:
            return pd.DataFrame(columns=["codigo", "transito_unidades"])

        df = pd.DataFrame([{"codigo": p.codigo, "cantidad_pendiente": p.cantidad_pendiente} for p in pendientes])
        return (
            df.groupby("codigo", as_index=False)["cantidad_pendiente"]
            .sum()
            .rename(columns={"cantidad_pendiente": "transito_unidades"})
        )

    def inconsistencias(self) -> list[dict]:
        return self._inconsistencias
