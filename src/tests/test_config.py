import json
import tempfile
import unittest
from pathlib import Path

from src.config import ConfigError, _fusionar, cargar_config

BASE_VALIDA = {
    "rutas": {
        "stock_carpeta": "STOCK",
        "stock_archivo": "stock.xlsx",
        "rubros_archivo": "rubros.xlsx",
        "stock_bebidas_archivo": "stock_bebidas.xlsx",
        "ventas_carpeta": "VENTAS",
        "transito_carpeta": "TRANSITO",
        "ingresos_archivo": "INGRESOS.xlsx",
        "novedades_archivo": "Novedades.xlsx",
        "supply_pedidos_carpeta": "Pedidos",
        "maestro_productos": "productos.xlsx",
        "salida": "salida",
        "logs": "logs",
    },
    "calculo": {
        "ventana_dias_venta": 7,
        "incluir_dia_actual": True,
        "contar_dias_turisticos": True,
        "redondeo_decimales": 2,
    },
    "semaforo_dias_stock": {"rojo_hasta": 3, "amarillo_hasta": 7, "verde_hasta": 20},
    "transito": {"dias_vencimiento_pendiente": 30},
    "semaforo_relativo_stock_seguridad": {"amarillo_hasta_multiplo": 2, "verde_hasta_multiplo": 5},
}


class TestFusionar(unittest.TestCase):
    def test_pisa_solo_la_clave_indicada(self):
        base = {"rutas": {"a": "1", "b": "2"}}
        override = {"rutas": {"a": "9"}}
        self.assertEqual(_fusionar(base, override), {"rutas": {"a": "9", "b": "2"}})

    def test_agrega_clave_nueva_sin_tocar_las_demas(self):
        base = {"rutas": {"a": "1"}, "calculo": {"x": 1}}
        override = {"otra_seccion": {"z": True}}
        resultado = _fusionar(base, override)
        self.assertEqual(resultado["rutas"], {"a": "1"})
        self.assertEqual(resultado["otra_seccion"], {"z": True})


class TestCargarConfigConOverride(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ruta = Path(self.tmp.name) / "config.json"
        self.ruta_local = Path(self.tmp.name) / "config.local.json"
        self.ruta.write_text(json.dumps(BASE_VALIDA), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_sin_config_local_usa_config_json_tal_cual(self):
        config = cargar_config(self.ruta, self.ruta_local)
        self.assertEqual(config.rutas.maestro_productos.name, "productos.xlsx")

    def test_config_local_pisa_solo_la_ruta_indicada(self):
        self.ruta_local.write_text(
            json.dumps({"rutas": {"maestro_productos": r"\\servidor\compartido\productos.xlsx"}}),
            encoding="utf-8",
        )
        config = cargar_config(self.ruta, self.ruta_local)
        self.assertEqual(str(config.rutas.maestro_productos), r"\\servidor\compartido\productos.xlsx")
        # El resto de las rutas no cambia por tener un config.local.json.
        self.assertEqual(config.rutas.stock_archivo, "stock.xlsx")

    def test_config_local_con_json_invalido_da_error_claro(self):
        self.ruta_local.write_text("{invalido", encoding="utf-8")
        with self.assertRaises(ConfigError):
            cargar_config(self.ruta, self.ruta_local)

    def test_sin_config_local_json_no_rompe(self):
        # El caso normal: la mayoria de las maquinas no tiene config.local.json.
        self.assertFalse(self.ruta_local.exists())
        cargar_config(self.ruta, self.ruta_local)  # no debe lanzar


if __name__ == "__main__":
    unittest.main()
