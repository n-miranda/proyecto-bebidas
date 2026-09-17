import unittest

from src.conversion import calcular_dias_stock, clasificar_riesgo, convertir_a_bultos, normalizar_codigo


class TestNormalizarCodigo(unittest.TestCase):
    def test_entero(self):
        self.assertEqual(normalizar_codigo(2826), "2826")

    def test_float_entero_de_excel(self):
        self.assertEqual(normalizar_codigo(2826.0), "2826")

    def test_string_con_espacios(self):
        self.assertEqual(normalizar_codigo("  2826  "), "2826")

    def test_none_lanza_error(self):
        with self.assertRaises(ValueError):
            normalizar_codigo(None)

    def test_vacio_lanza_error(self):
        with self.assertRaises(ValueError):
            normalizar_codigo("   ")


class TestConvertirABultos(unittest.TestCase):
    def test_conversion_normal(self):
        self.assertAlmostEqual(convertir_a_bultos(240, 12), 20.0)

    def test_unidades_por_bulto_cero_usa_uno(self):
        self.assertAlmostEqual(convertir_a_bultos(5, 0), 5.0)

    def test_unidades_por_bulto_none_usa_uno(self):
        self.assertAlmostEqual(convertir_a_bultos(5, None), 5.0)


class TestCalcularDiasStock(unittest.TestCase):
    """Casos borde de la tabla CLAUDE.md seccion 5.4."""

    def test_sin_venta_con_stock_devuelve_none(self):
        self.assertIsNone(calcular_dias_stock(stock_bultos=10, promedio_diario_bultos=0))

    def test_sin_venta_sin_stock_devuelve_none(self):
        self.assertIsNone(calcular_dias_stock(stock_bultos=0, promedio_diario_bultos=0))

    def test_stock_en_cero_con_venta_devuelve_cero(self):
        self.assertEqual(calcular_dias_stock(stock_bultos=0, promedio_diario_bultos=2), 0.0)

    def test_stock_negativo_con_venta_devuelve_cero(self):
        self.assertEqual(calcular_dias_stock(stock_bultos=-3, promedio_diario_bultos=2), 0.0)

    def test_caso_normal(self):
        self.assertAlmostEqual(calcular_dias_stock(stock_bultos=20, promedio_diario_bultos=4), 5.0)

    def test_venta_neta_negativa_devuelve_valor_tal_cual(self):
        # Devoluciones > ventas en la ventana: se muestra el numero crudo,
        # sin tratamiento especial (decision explicita del usuario).
        resultado = calcular_dias_stock(stock_bultos=0.42, promedio_diario_bultos=-0.024)
        self.assertAlmostEqual(resultado, -17.5, places=1)


class TestClasificarRiesgo(unittest.TestCase):
    """Umbrales fijos de config (rojo_hasta=3, amarillo_hasta=7, verde_hasta=20)
    vs. politica relativa por producto (St Seg/D St, multiplos 2x/5x -- caso
    confirmado con el usuario el 2026-09-08: Piamontesa codigo 1011, St Seg=7)."""

    UMBRAL_ROJO, UMBRAL_AMARILLO, UMBRAL_VERDE = 3, 7, 20
    MULTIPLO_AMARILLO, MULTIPLO_VERDE = 2, 5

    def _clasificar(self, dias_stock, dias_stock_seguridad=None):
        return clasificar_riesgo(
            dias_stock, dias_stock_seguridad,
            self.UMBRAL_ROJO, self.UMBRAL_AMARILLO, self.UMBRAL_VERDE,
            self.MULTIPLO_AMARILLO, self.MULTIPLO_VERDE,
        )

    def test_sin_venta_es_neutro(self):
        self.assertEqual(self._clasificar(None), "neutro")

    def test_sin_politica_usa_umbral_fijo(self):
        self.assertEqual(self._clasificar(2), "rojo")
        self.assertEqual(self._clasificar(5), "amarillo")
        self.assertEqual(self._clasificar(15), "verde")
        self.assertEqual(self._clasificar(25), "sobrestock")

    def test_con_politica_rojo_por_debajo_del_piso(self):
        # St Seg=7: por debajo de 7 es rojo, sin importar el umbral fijo (3)
        self.assertEqual(self._clasificar(5, dias_stock_seguridad=7), "rojo")

    def test_con_politica_amarillo_entre_1x_y_2x(self):
        self.assertEqual(self._clasificar(10, dias_stock_seguridad=7), "amarillo")

    def test_con_politica_verde_entre_2x_y_5x(self):
        self.assertEqual(self._clasificar(20, dias_stock_seguridad=7), "verde")

    def test_con_politica_sobrestock_mas_alla_de_5x(self):
        self.assertEqual(self._clasificar(40, dias_stock_seguridad=7), "sobrestock")

    def test_piso_en_cero_o_none_no_rompe_cae_a_umbral_fijo(self):
        self.assertEqual(self._clasificar(2, dias_stock_seguridad=0), "rojo")  # 2 < umbral fijo 3
        self.assertEqual(self._clasificar(15, dias_stock_seguridad=None), "verde")


if __name__ == "__main__":
    unittest.main()
