import unittest
from datetime import date

from src.calendario import CalendarioError, Feriados, cargar_feriados, es_dia_de_venta, ventana_dias_venta


class TestEsDiaDeVenta(unittest.TestCase):
    def setUp(self):
        self.feriados = Feriados(
            anio=2026,
            inamovibles={date(2026, 1, 1)},
            trasladables={date(2026, 6, 15)},
            turisticos={date(2026, 3, 23)},
        )

    def test_domingo_no_es_dia_de_venta(self):
        # 2026-08-30 es domingo
        self.assertFalse(es_dia_de_venta(date(2026, 8, 30), self.feriados))

    def test_sabado_si_es_dia_de_venta(self):
        # 2026-08-29 es sabado
        self.assertTrue(es_dia_de_venta(date(2026, 8, 29), self.feriados))

    def test_feriado_inamovible_no_es_dia_de_venta(self):
        self.assertFalse(es_dia_de_venta(date(2026, 1, 1), self.feriados))

    def test_feriado_trasladable_no_es_dia_de_venta(self):
        self.assertFalse(es_dia_de_venta(date(2026, 6, 15), self.feriados))

    def test_turistico_cuenta_por_defecto(self):
        self.assertTrue(es_dia_de_venta(date(2026, 3, 23), self.feriados, contar_dias_turisticos=True))

    def test_turistico_no_cuenta_si_se_desactiva(self):
        self.assertFalse(es_dia_de_venta(date(2026, 3, 23), self.feriados, contar_dias_turisticos=False))

    def test_dia_habil_normal(self):
        self.assertTrue(es_dia_de_venta(date(2026, 8, 25), self.feriados))


class TestCargarFeriados(unittest.TestCase):
    def test_anio_2026_carga_ok(self):
        feriados = cargar_feriados(2026)
        self.assertIn(date(2026, 1, 1), feriados.inamovibles)
        self.assertIn(date(2026, 6, 15), feriados.trasladables)
        self.assertIn(date(2026, 3, 23), feriados.turisticos)

    def test_anio_sin_datos_falla_con_error_claro(self):
        with self.assertRaises(CalendarioError):
            cargar_feriados(1999)


class TestVentanaDiasVenta(unittest.TestCase):
    def test_ventana_de_7_dias_desde_2026_09_01(self):
        # 2026-09-01 es dia de venta (martes, sin feriado). Retrocediendo se
        # salta el domingo 2026-08-30.
        dias = ventana_dias_venta(date(2026, 9, 1), n=7, incluir_dia_actual=True)
        self.assertEqual(len(dias), 7)
        self.assertEqual(dias[-1], date(2026, 9, 1))
        self.assertNotIn(date(2026, 8, 30), dias)  # domingo
        self.assertEqual(dias, sorted(dias))

    def test_sin_incluir_dia_actual_arranca_el_dia_anterior(self):
        dias = ventana_dias_venta(date(2026, 9, 1), n=7, incluir_dia_actual=False)
        self.assertNotIn(date(2026, 9, 1), dias)
        self.assertEqual(dias[-1], date(2026, 8, 31))


if __name__ == "__main__":
    unittest.main()
