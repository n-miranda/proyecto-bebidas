"""Mapa carpeta-de-proveedor (nombre exacto en Supply\\Posadas\\2. Pedidos
Posadas) -> funcion extractora. PAPEL queda afuera a proposito: en
AUTOMATIZACION_PEDIDOS_CONTROL se verifico que esos archivos no son pedidos
genuinos de ese proveedor (resuelven a otro proveedor)."""
from . import georgalos, la_serenisima, piamontesa, timbo, trigos_argentinos

EXTRACTORES = {
    "GEORGALOS": georgalos.extraer,
    "La Serenisima": la_serenisima.extraer,
    "Piamontesa": piamontesa.extraer,
    "TIMBO": timbo.extraer,
    "TRIGOS ARGENTINOS": trigos_argentinos.extraer,
}
