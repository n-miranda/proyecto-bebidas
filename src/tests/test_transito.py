import json
import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import openpyxl

from src.fuentes.excel_transito import TransitoSupplyIngresos


def _crear_ingresos_xlsx(ruta: Path, filas: list[tuple]) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "INGRESOS"
    ws.append(["Codigo Producto", "Producto", "Cantidad", "INGRESO", "PEDIDO"])
    for fila in filas:
        ws.append(list(fila))
    wb.save(ruta)


def _crear_fuente(tmp: Path, dias_vencimiento: int = 30) -> TransitoSupplyIngresos:
    supply = tmp / "Supply"
    supply.mkdir(exist_ok=True)  # vacia: sin proveedores, no aporta pedidos nuevos
    estado = tmp / "salida"
    estado.mkdir(exist_ok=True)
    return TransitoSupplyIngresos(
        supply_pedidos_carpeta=supply,
        ingresos_archivo=tmp / "INGRESOS.xlsx",
        estado_carpeta=estado,
        dias_vencimiento=dias_vencimiento,
    )


def _sembrar_pendientes(fuente: TransitoSupplyIngresos, pendientes: list[dict]) -> None:
    fuente.ruta_pendientes.parent.mkdir(parents=True, exist_ok=True)
    fuente.ruta_pendientes.write_text(json.dumps(pendientes), encoding="utf-8")


class TestCrucePorFechaExacta(unittest.TestCase):
    def test_match_exacto_por_fecha_pedido(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fuente = _crear_fuente(tmp)
            _sembrar_pendientes(fuente, [
                {"codigo": "100", "proveedor": "GEORGALOS", "cantidad_pedida": 50,
                 "cantidad_pendiente": 50, "fecha_pedido": "2026-08-01", "archivo_origen": "a.xlsx"},
                {"codigo": "100", "proveedor": "GEORGALOS", "cantidad_pedida": 30,
                 "cantidad_pendiente": 30, "fecha_pedido": "2026-08-15", "archivo_origen": "b.xlsx"},
            ])
            _crear_ingresos_xlsx(tmp / "INGRESOS.xlsx", [
                (100, "PRODUCTO X", 30, date(2026, 8, 20), date(2026, 8, 15)),
            ])
            df = fuente.leer()
            # debe descontar del pedido del 15/8 (match exacto), no del mas viejo
            total_pendiente = df[df["codigo"] == "100"]["transito_unidades"].sum()
            self.assertEqual(total_pendiente, 50)


class TestCruceFIFO(unittest.TestCase):
    def test_sin_fecha_exacta_usa_el_pendiente_mas_antiguo(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fuente = _crear_fuente(tmp)
            _sembrar_pendientes(fuente, [
                {"codigo": "200", "proveedor": "TIMBO", "cantidad_pedida": 20,
                 "cantidad_pendiente": 20, "fecha_pedido": "2026-08-01", "archivo_origen": "a.xlsx"},
                {"codigo": "200", "proveedor": "TIMBO", "cantidad_pedida": 20,
                 "cantidad_pendiente": 20, "fecha_pedido": "2026-08-10", "archivo_origen": "b.xlsx"},
            ])
            # el ingreso trae una fecha de pedido que no coincide con ninguna -> FIFO
            _crear_ingresos_xlsx(tmp / "INGRESOS.xlsx", [
                (200, "PRODUCTO Y", 20, date(2026, 8, 20), date(2026, 8, 5)),
            ])
            fuente.leer()
            pendientes = json.loads(fuente.ruta_pendientes.read_text(encoding="utf-8"))
            restante = {p["fecha_pedido"]: p["cantidad_pendiente"] for p in pendientes}
            self.assertEqual(restante.get("2026-08-01", 0), 0)  # se consumio el mas viejo
            self.assertEqual(restante["2026-08-10"], 20)  # el mas nuevo queda intacto


class TestEntregaParcial(unittest.TestCase):
    def test_ingreso_menor_al_pedido_deja_resto_pendiente(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fuente = _crear_fuente(tmp)
            _sembrar_pendientes(fuente, [
                {"codigo": "300", "proveedor": "PIAMONTESA", "cantidad_pedida": 100,
                 "cantidad_pendiente": 100, "fecha_pedido": "2026-08-01", "archivo_origen": "a.xlsx"},
            ])
            _crear_ingresos_xlsx(tmp / "INGRESOS.xlsx", [
                (300, "PRODUCTO Z", 40, date(2026, 8, 5), date(2026, 8, 1)),
            ])
            df = fuente.leer()
            self.assertEqual(df[df["codigo"] == "300"]["transito_unidades"].iloc[0], 60)


class TestExcedenteSinMatch(unittest.TestCase):
    def test_ingreso_sin_pendiente_se_reporta_y_persiste(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fuente = _crear_fuente(tmp)
            _crear_ingresos_xlsx(tmp / "INGRESOS.xlsx", [
                (400, "PRODUCTO SORPRESA", 10, date(2026, 8, 5), date(2026, 8, 1)),
            ])
            fuente.leer()
            inconsistencias = fuente.inconsistencias()
            self.assertEqual(len(inconsistencias), 1)
            self.assertIn("sin pedido pendiente", inconsistencias[0]["motivo"])

            # segunda corrida: el archivo de ingresos no cambio, pero la
            # inconsistencia NO debe desaparecer del reporte
            fuente2 = _crear_fuente(tmp)
            fuente2.leer()
            self.assertEqual(len(fuente2.inconsistencias()), 1)


class TestVencimiento(unittest.TestCase):
    def test_pedido_viejo_se_reporta_pero_no_se_borra(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fuente = _crear_fuente(tmp, dias_vencimiento=30)
            fecha_vieja = (date.today() - timedelta(days=45)).isoformat()
            _sembrar_pendientes(fuente, [
                {"codigo": "500", "proveedor": "GEORGALOS", "cantidad_pedida": 10,
                 "cantidad_pendiente": 10, "fecha_pedido": fecha_vieja, "archivo_origen": "a.xlsx"},
            ])
            df = fuente.leer()
            # sigue contando en transito (no se oculta el numero)
            self.assertEqual(df[df["codigo"] == "500"]["transito_unidades"].iloc[0], 10)
            motivos = [i["motivo"] for i in fuente.inconsistencias()]
            self.assertTrue(any("pendiente hace mas de" in m for m in motivos))


class TestIdempotencia(unittest.TestCase):
    def test_segunda_corrida_sin_cambios_no_reprocesa(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            fuente = _crear_fuente(tmp)
            _sembrar_pendientes(fuente, [
                {"codigo": "600", "proveedor": "TIMBO", "cantidad_pedida": 50,
                 "cantidad_pendiente": 50, "fecha_pedido": "2026-08-01", "archivo_origen": "a.xlsx"},
            ])
            _crear_ingresos_xlsx(tmp / "INGRESOS.xlsx", [
                (600, "PRODUCTO W", 20, date(2026, 8, 5), date(2026, 8, 1)),
            ])
            df1 = fuente.leer()
            self.assertEqual(df1[df1["codigo"] == "600"]["transito_unidades"].iloc[0], 30)

            fuente2 = _crear_fuente(tmp)
            df2 = fuente2.leer()
            # mismo archivo de ingresos, ninguna fila nueva -> no se vuelve a descontar
            self.assertEqual(df2[df2["codigo"] == "600"]["transito_unidades"].iloc[0], 30)


if __name__ == "__main__":
    unittest.main()
