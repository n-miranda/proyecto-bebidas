# PROYECTO BEBIDAS — Instrucciones del proyecto

> **Ubicación de este archivo:** `D:\PROYECTO BEBIDAS\CLAUDE.md`
> Claude Code lo lee automáticamente al abrir la carpeta del proyecto en VS Code.
> Antes de escribir la primera línea de código, leer este archivo completo y
> ejecutar el **Paso 0 — Reconocimiento** (sección 12).

> ⚠️ **Este proyecto nace como copia de `D:\UNIFICADOR_STOCK`**, pensado para
> terminar unificando el stock de otra línea de productos (bebidas) en vez de
> refrigerados. **Por pedido explícito del usuario (2026-09-17), por el
> momento sigue trabajando contra las mismas bases** (`STOCK\stock.xlsx`,
> `STOCK\rubros.xlsx`, `VENTAS\VENTAS.xlsx`, `TRANSITO\INGRESOS.xlsx`, el
> maestro de productos y la carpeta de pedidos de Posadas) — es, en los
> hechos, una copia funcional en paralelo de UNIFICADOR_STOCK, no todavía una
> herramienta de bebidas con datos propios. Por eso `config\config.json` y
> `config\mapeo_columnas.json` son **idénticos** a los de UNIFICADOR_STOCK y
> siguen siendo válidos tal cual, incluidos los parsers de
> `src\fuentes\pedidos_posadas\` (Georgalos, La Serenisima, Piamontesa, Timbo,
> Trigos Argentinos) y la exclusión de BIGAR SA / MOLINOS RIO DE LA PLATA.
>
> **Cuando llegue el momento de apuntar a datos reales de bebidas:** hay que
> repetir el **Paso 0 — Reconocimiento** (sección 12) contra esos archivos
> nuevos, porque nada garantiza que compartan el mismo formato, columnas,
> proveedores o unidades por bulto que Total Refrigerados. Hasta entonces, dos
> proyectos corriendo sobre las mismas bases significa que un cambio de
> config en uno no se refleja en el otro — mantenerlo en cuenta al editar.

---

## 1. Objetivo del proyecto

Construir una **aplicación web local** que unifique, en una sola vista, el control
de stock de bebidas, tomando datos de distintas fuentes y mostrando
por artículo:

| Dato | Descripción |
|---|---|
| Código de artículo | Clave única, la misma que usa el ERP Chess |
| Descripción | Nombre del artículo |
| Stock en bultos | Stock actual convertido de unidades a bultos/cajas |
| Promedio de ventas | Venta diaria promedio de los últimos 7 **días de venta** |
| Días de stock | Cuántos días de venta cubre el stock actual |
| Tránsito | Pedidos generados y todavía no recibidos |

Con **filtros por proveedor y por rubro**.

**Objetivo de negocio:** detectar de un vistazo qué artículos están por quebrar
stock y cuáles están sobrestockeados, sin tener que cruzar planillas a mano.

---

## 2. Alcance

### Fase 1 (esta etapa — pruebas)
- Fuentes de datos = archivos **Excel** depositados en carpetas locales.
- Ejecución **100 % local** (no hay servidor, no hay nube, no hay base de datos).
- Un comando actualiza los datos, la web muestra el resultado.

### Fuera de alcance por ahora (pero la arquitectura debe permitirlo)
- Conexión directa al ERP Chess (ver sección 11).
- Escritura de datos hacia el ERP. **La app es de solo lectura.**
- Multiusuario, login, despliegue en red.

---

## 3. Stack técnico

| Capa | Tecnología | Motivo |
|---|---|---|
| Procesamiento | Python 3.11+, `pandas`, `openpyxl` | Ya usado en el resto de las automatizaciones |
| Backend web | `Flask` | Liviano, sin build, corre con doble clic |
| Frontend | HTML + CSS + JavaScript vanilla | Sin Node, sin bundler, sin dependencias que mantener |
| Tabla | Ordenamiento y filtrado en JS del lado cliente | El volumen esperado (miles de filas) lo soporta sin problema |

**Restricciones duras:**
- Nada que requiera internet en tiempo de ejecución (salvo CDNs opcionales; si se
  usan, dejar fallback local).
- Nada de fórmulas de Excel: **todo el cálculo va en Python**.
- Debe correr en Windows sin permisos de administrador.

### Estructura de carpetas a crear

```
D:\PROYECTO BEBIDAS\
├── CLAUDE.md                  <- este archivo
├── README.md                  <- instrucciones de uso para el usuario final
├── requirements.txt
├── actualizar.bat             <- doble clic: procesa datos y levanta la web
├── config\
│   ├── config.json            <- rutas, parámetros de negocio
│   ├── feriados.json          <- feriados nacionales argentinos
│   └── mapeo_columnas.json    <- mapeo de columnas de cada fuente
├── src\
│   ├── main.py                <- punto de entrada (procesa + levanta Flask)
│   ├── config.py              <- carga y valida config.json
│   ├── calendario.py          <- días de venta, feriados, ventana de 7 días
│   ├── conversion.py          <- unidades <-> bultos, maestro de productos
│   ├── fuentes\
│   │   ├── base.py            <- interfaz abstracta de fuente de datos
│   │   ├── excel_stock.py
│   │   ├── excel_ventas.py
│   │   └── excel_transito.py
│   ├── consolidador.py        <- arma el DataFrame canónico final
│   └── web\
│       ├── app.py             <- rutas Flask + API JSON
│       ├── templates\index.html
│       └── static\{app.js, estilos.css}
├── STOCK\                     <- bases de stock (input, ya existe)
├── VENTAS\                    <- bases de ventas (input, ya existe)
├── TRANSITO\                  <- pedidos pendientes (input, A DEFINIR)
├── salida\
│   └── snapshot.json          <- resultado consolidado que consume la web
└── logs\
    └── unificador_AAAAMMDD.log
```

---

## 4. Fuentes de datos

> ⚠️ Los mapeos de columnas de abajo (secciones 4.1-4.3) son las **hipótesis
> originales** con las que arrancó UNIFICADOR_STOCK y, tras su Paso 0 real,
> terminaron **no coincidiendo** (stock quedó en columnas A/B/C, no G; ventas
> en A/B/C/D con fecha propia, no R/AO). El mapeo realmente vigente hoy —
> tanto para UNIFICADOR_STOCK como para este proyecto mientras use las mismas
> bases — es el confirmado en `config\mapeo_columnas.json`, no el de esta
> sección. **El día que PROYECTO BEBIDAS pase a usar archivos propios de
> bebidas, hay que repetir el Paso 0 contra esos archivos y reescribir
> `config\mapeo_columnas.json`** — no asumir que el mapeo actual sigue
> valiendo solo porque el código no cambió.

### 4.1 STOCK — `D:\PROYECTO BEBIDAS\STOCK\`
- Formato: Excel export del ERP.
- Unidad: **unidades** (no bultos).
- Hipótesis: código de artículo en la primera columna de código disponible;
  **columna G = unidades de stock**.
- Si hay más de un archivo, tomar el **más reciente por fecha de modificación** y
  registrar en el log cuál se usó.

### 4.2 VENTAS — `D:\PROYECTO BEBIDAS\VENTAS\`
- Formato: Excel export del ERP.
- Unidad: **unidades**.
- Hipótesis de mapeo: **columna R = código de artículo**, **columna AO = venta en
  unidades**.
- Las ventas se **suman** por código y fecha; los valores negativos (devoluciones,
  notas de crédito) **se restan**, no se descartan.
- **Fecha del movimiento:** identificar la columna de fecha en el export. Si el
  export no la trae, la fecha se deduce del nombre del archivo (un archivo por
  día). Determinar cuál de los dos casos aplica en el Paso 0 y dejarlo
  documentado.
- Se leen **todos** los archivos de la carpeta y se filtra por la ventana de 7
  días de venta (sección 5.2). Descartar duplicados por (archivo, fila) si el
  mismo día aparece en dos archivos.

### 4.3 Maestro de productos (conversión a bultos)
- **Antes de implementar la conversión, leer el archivo `.md` que está en
  `D:\AUTOMATIZACION_PEDIDOS_CONTROL\`.** Ahí está documentada la lógica de
  conversión ya validada. Respetarla; no reinventarla.
- Hipótesis de partida del maestro `productos`: **col A = código**,
  **col E = proveedor**, **col F = unidades por caja/bulto**.
- **El campo `rubro` es requerido por el filtro B de la especificación.** Si el
  maestro no lo tiene, marcarlo como bloqueante y consultarlo (ver sección 13).

### 4.4 TRÁNSITO — `D:\PROYECTO BEBIDAS\TRANSITO\`
- **Por el momento usa la misma solución que UNIFICADOR_STOCK**, porque
  comparte la misma base de datos: parsers por proveedor de Posadas
  (`src\fuentes\pedidos_posadas\`: Georgalos, La Serenisima, Piamontesa, Timbo,
  Trigos Argentinos) que leen `config.rutas.supply_pedidos_carpeta`, más la
  planilla manual `TRANSITO\INGRESOS.xlsx` que el usuario carga a mano. Sigue
  vigente tal cual mientras no cambien las bases.
- **Cuando bebidas tenga proveedores y fuente de tránsito propios**, ninguno
  de esos parsers específicos de Posadas va a aplicar — hay que definir el
  origen real (ver preguntas abiertas, sección 13) y, si hace falta, escribir
  parsers nuevos o volver al adaptador simple contra `fuentes/base.py`
  descripto abajo.
- Adaptador mínimo: un Excel simple con las columnas mínimas:
  `codigo | cantidad | unidad (UNI|BUL) | fecha_pedido | fecha_estimada_llegada | proveedor`
- Si la carpeta está vacía o no existe, la app **debe funcionar igual**, con
  tránsito = 0 y un aviso visible en la interfaz.

### 4.5 DataFrame canónico (salida del consolidador)

Toda fuente, sea Excel hoy o Chess mañana, se normaliza a esta estructura:

```
codigo                 str    (clave, siempre string, sin espacios, sin ceros a la izquierda perdidos)
descripcion            str
proveedor              str
rubro                  str
unidades_por_bulto     int
stock_unidades         float
stock_bultos           float
venta_unidades_7d      float
promedio_diario_uni    float
promedio_diario_bultos float
dias_stock             float | None
transito_bultos        float
dias_stock_c_transito  float | None
dias_venta_usados      int    (cuántos días de venta reales entraron en el promedio)
```

**Regla de oro del cruce:** el código de artículo se normaliza SIEMPRE con la
misma función (`normalizar_codigo()`) antes de cualquier join. Es la causa número
uno de errores silenciosos en este tipo de cruces.

**Artículos huérfanos:** si un código aparece en ventas o stock pero no en el
maestro de productos, **no se descarta**: se muestra con `unidades_por_bulto = 1`,
proveedor/rubro = "SIN CLASIFICAR" y se lista en un reporte de inconsistencias al
final de la corrida. Lo mismo para los que no tienen unidades por bulto cargadas.

---

## 5. Reglas de negocio

### 5.1 Días de venta

Un día es **día de venta** si **NO** es:
- domingo, ni
- feriado nacional argentino (ver `config\feriados.json`, sección 6).

Los **días no laborables con fines turísticos** (los "puentes") **SÍ cuentan como
día de venta por defecto**, porque no son feriados obligatorios y la operación
normalmente trabaja. Es configurable con la clave `contar_dias_turisticos`
(default `true`).

Los sábados **sí cuentan** como día de venta.

### 5.2 Ventana de 7 días

- Se toman los **últimos 7 días de venta** contando hacia atrás desde la fecha de
  actualización (hoy), **incluyendo hoy** si hoy es día de venta.
- Es decir: se retrocede en el calendario salteando domingos y feriados hasta
  juntar 7 días válidos. La ventana puede abarcar 8, 9 o más días corridos.
- El promedio siempre se divide por **7** (la cantidad de días de venta de la
  ventana), no por los días corridos.

```python
# Pseudocódigo
dias = []
d = hoy
while len(dias) < 7:
    if es_dia_de_venta(d):
        dias.append(d)
    d -= timedelta(days=1)
```

> ⚠️ **Advertencia a tener en cuenta:** incluir el día en curso mete un día
> **parcial** en el promedio (todavía no terminó de facturarse), lo que empuja el
> promedio hacia abajo y sobreestima los días de stock. Por eso debe existir el
> parámetro `incluir_dia_actual` en `config.json`. Default `true` según la
> especificación, pero dejar el flag y documentarlo en el README, porque si la
> actualización se corre a la mañana el efecto es importante.

### 5.3 Conversión a bultos

```
stock_bultos           = stock_unidades / unidades_por_bulto
promedio_diario_bultos = promedio_diario_uni / unidades_por_bulto
transito_bultos        = si viene en unidades, dividir; si viene en bultos, tal cual
```
- Redondeo a **2 decimales** solo para mostrar. Los cálculos internos van con
  precisión completa.
- `unidades_por_bulto` nunca puede ser 0 → si lo es o falta, usar 1 y reportar.

### 5.4 Días de stock

```
dias_stock            = stock_bultos / promedio_diario_bultos
dias_stock_c_transito = (stock_bultos + transito_bultos) / promedio_diario_bultos
```
Casos borde, todos obligatorios:

| Situación | Resultado | Se muestra |
|---|---|---|
| `promedio_diario == 0` y `stock > 0` | `None` | `S/V` (sin venta) |
| `promedio_diario == 0` y `stock == 0` | `None` | `—` |
| `stock <= 0` y hay venta | `0` | `0` en rojo |
| Normal | número | 1 decimal |

**Nunca dividir por cero ni devolver `inf`.**

### 5.5 Formato de salida (convención argentina)
- Decimales con **coma**, miles con **punto**: `1.234,56`.
- Fechas `DD/MM/AAAA`.
- El formateo se hace en el frontend (`Intl.NumberFormat('es-AR')`); el JSON de
  la API viaja siempre con números crudos en formato estándar.

---

## 6. Feriados — `config\feriados.json`

Archivo editable a mano, un año por clave. Estructura:

```json
{
  "2026": {
    "inamovibles": [
      "2026-01-01", "2026-02-16", "2026-02-17", "2026-03-24",
      "2026-04-02", "2026-04-03", "2026-05-01", "2026-05-25",
      "2026-06-20", "2026-07-09", "2026-12-08", "2026-12-25"
    ],
    "trasladables": ["2026-06-15", "2026-08-17", "2026-10-12", "2026-11-23"],
    "turisticos": ["2026-03-23", "2026-07-10", "2026-12-07"]
  }
}
```

Notas importantes:
- Los **trasladables** ya están con la fecha efectiva del traslado, no la
  original (ej.: Soberanía Nacional pasa del viernes 20/11 al lunes 23/11).
- **Verificar el feriado de Güemes** (17/06, cae miércoles en 2026 → traslado al
  lunes 15/06) contra el calendario oficial de Jefatura de Gabinete antes de
  darlo por bueno.
- El sistema debe **fallar con un error claro** si se pide calcular sobre un año
  que no está cargado en el archivo, en vez de asumir que no hay feriados.
- No hardcodear feriados en el código Python bajo ninguna circunstancia.

---

## 7. La web

### 7.1 API (Flask)

| Endpoint | Devuelve |
|---|---|
| `GET /` | La página |
| `GET /api/stock` | Array de artículos (DataFrame canónico serializado) |
| `GET /api/meta` | Fecha de actualización, archivos usados, días de venta de la ventana, cantidad de inconsistencias |
| `POST /api/actualizar` | Reprocesa las bases y regenera el snapshot |

La web **lee `salida\snapshot.json`**, no procesa Excel en cada request.

### 7.2 Interfaz

Estilo: **corporativo, sobrio, orientado a decisión rápida**. Sin adornos.

- **Barra superior:** título, fecha/hora de la última actualización, botón
  "Actualizar datos", aviso si alguna fuente faltó.
- **Filtros:** desplegable de **proveedor**, desplegable de **rubro**, buscador
  libre por código/descripción, y un check "solo artículos críticos".
  Los filtros son combinables y se aplican en vivo.
- **Tabla:** columnas ordenables por clic. Orden inicial: `dias_stock` ascendente
  (lo más crítico arriba).
- **Semáforo sobre `días de stock`** (umbrales en `config.json`, no hardcodeados):

  | Rango | Color | Significado |
  |---|---|---|
  | < 3 días | rojo | Riesgo de quiebre |
  | 3 a 7 días | amarillo | Atención |
  | 7 a 20 días | verde | Normal |
  | > 20 días | azul/gris | Sobrestock |

- **Tránsito:** columna propia. Si un artículo está en rojo pero tiene tránsito,
  mostrarlo con un ícono para distinguir "quiebre real" de "quiebre cubierto".
- **Totales** al pie: cantidad de artículos filtrados, cuántos en rojo, cuántos
  en sobrestock.
- **Exportar a Excel/CSV** lo que está filtrado en pantalla.
- Debe verse bien en pantalla de escritorio; no hace falta responsive de celular.

---

## 8. Fases de implementación

Trabajar **de a una fase, con validación del usuario antes de pasar a la
siguiente**. No adelantarse.

**Fase 0 — Reconocimiento (sin escribir código de producción)**
Ver sección 12. Entregable: un resumen de qué trae realmente cada archivo.

**Fase 1 — Motor de cálculo (CLI)**
`calendario.py` + `conversion.py` + lectura de STOCK y VENTAS + consolidador.
Entregable: script que imprime por consola 10 artículos con todas sus columnas
calculadas.
*Criterio de aceptación:* el usuario verifica a mano 3 artículos y los números
coinciden.

**Fase 2 — Web básica**
Flask + tabla + carga del snapshot.
*Criterio de aceptación:* la tabla muestra todos los artículos y ordena.

**Fase 3 — Filtros y semáforo**
Proveedor, rubro, buscador, colores, totales, exportar.

**Fase 4 — Tránsito**
Una vez definida la fuente (sección 13).

**Fase 5 — Empaquetado**
`actualizar.bat`, README, manejo de errores amigable, logs.

---

## 9. Convenciones de código

- Python: nombres y comentarios en **español**, `snake_case`, type hints.
- **Toda ruta sale de `config.json`.** Cero rutas hardcodeadas en el código.
- **Toda regla de negocio con número** (umbrales, cantidad de días, redondeos)
  sale de `config.json`.
- Logging a `logs\` con nivel INFO: qué archivo se leyó, cuántas filas, qué días
  de venta se usaron, cuántos huérfanos aparecieron.
- Los errores esperables (falta un archivo, falta una columna, carpeta vacía) se
  reportan con mensaje claro en castellano; nada de stack traces crudos en la
  cara del usuario.
- Cada función de cálculo (`dias_stock`, `promedio`, `es_dia_de_venta`) con su
  test unitario, incluyendo los casos borde de la tabla 5.4.
- **Preferir refinamiento iterativo sobre reescrituras completas:** si algo hay
  que cambiar, cambiar esa parte, no rehacer el módulo.

---

## 10. Rendimiento

Objetivo: la actualización completa debe correr en **menos de 60 segundos**. Si
la lectura de VENTAS se vuelve lenta por la cantidad de archivos, cachear los
días ya procesados en `salida\cache_ventas.parquet` y releer solo los días
nuevos.

---

## 11. Migración futura al ERP

> ⚠️ **Heredado de UNIFICADOR_STOCK, revisar para bebidas.** Esa investigación
> (Chess/Nextbyn sin API pública, ir a SQL Server directo) es específica del
> ERP que usa Total Refrigerados. **Falta confirmar qué ERP/sistema usa el
> área de bebidas** (¿el mismo Chess? ¿otro?) antes de asumir que aplica el
> mismo camino.

La especificación menciona extraer los datos vía API del ERP. **Dato relevante
ya investigado para Chess (Nextbyn): no expone una API pública documentada.**
Si bebidas usa el mismo ERP, los caminos realistas son:

1. **Conexión directa a SQL Server** (solo lectura, usuario dedicado con permisos
   mínimos) → es la vía más probable y la más rápida de implementar.
2. **Consulta formal a Nextbyn** por una API o vistas soportadas, para no quedar
   atado a un esquema interno que pueden cambiar sin aviso.

**Implicancia de diseño, no negociable:** las fuentes de datos van detrás de la
interfaz `fuentes/base.py`. Cambiar de Excel a SQL debe implicar escribir un
adaptador nuevo (`sql_stock.py`) y cambiar una línea en `config.json`, **sin
tocar el consolidador, el cálculo ni la web**.

---

## 12. Paso 0 — Reconocimiento (hacer esto primero)

> ⚠️ Este paso hay que **rehacerlo desde cero para bebidas** aunque ya exista un
> `config\mapeo_columnas.json` en este proyecto: ese archivo describe los
> Excel reales de Total Refrigerados (heredados de UNIFICADOR_STOCK), no los
> de bebidas.

Antes de escribir código de producción, generar un script descartable que:

1. Liste todos los archivos de `STOCK\` y `VENTAS\` (y, si existe y aplica a
   bebidas, `D:\AUTOMATIZACION_PEDIDOS_CONTROL\` — proyecto de Total
   Refrigerados; usarlo solo como referencia de lógica de conversión, no dar
   por sentado que comparte maestro de productos con bebidas).
2. Si aplica, lea el `.md` de `AUTOMATIZACION_PEDIDOS_CONTROL` y resuma la
   lógica de conversión a bultos documentada ahí.
3. Para cada Excel: nombre de hojas, encabezados reales, tipos de dato, 5 filas
   de muestra, cantidad de filas.
4. Confirme o corrija las hipótesis de mapeo de la sección 4.
5. Verifique si el maestro de productos tiene **rubro** y **proveedor**.
6. Verifique si el export de ventas tiene **columna de fecha**.
7. Chequee el formato del código de artículo en cada fuente (¿string?, ¿número?,
   ¿ceros a la izquierda?) → define `normalizar_codigo()`.

**Entregable:** un resumen en pantalla + `config\mapeo_columnas.json` propuesto.
Recién con eso confirmado se arranca la Fase 1.

---

## 13. Preguntas abiertas (consultar antes de asumir)

> Estas reemplazan a las de UNIFICADOR_STOCK (eran específicas de Posadas/TRP).

1. **ERP/sistema de origen:** ¿bebidas usa el mismo Chess que Total
   Refrigerados, u otro sistema? Define si aplica la sección 11 tal cual.
2. **Maestro de productos:** ¿existe uno propio de bebidas (código, proveedor,
   unidades por bulto, rubro), o hay que armarlo? ¿Es el mismo archivo que usa
   Total Refrigerados o uno separado?
3. **Tránsito:** ¿de dónde salen los pedidos pendientes de bebidas? ¿Export del
   ERP, planillas manuales de compras, o carga manual dedicada? ¿En qué unidad
   vienen? ¿Cómo se sabe que un pedido ya se recibió y sale del tránsito? (En
   UNIFICADOR_STOCK esto terminó resolviéndose con parsers por proveedor —
   ver `src\fuentes\pedidos_posadas\` — que no aplican a los proveedores de
   bebidas.)
4. **Rubro:** ¿está en el maestro de productos de bebidas o hay que traerlo de
   otro lado?
5. **Alcance de depósitos/sucursales:** ¿esta herramienta es para un solo
   depósito de bebidas o hay que unificar varios? Si son varios, hace falta
   una columna de depósito y un filtro más.
6. **Frecuencia:** ¿la actualización se dispara a mano cuando se abre la web, o
   tiene que correr sola a una hora fija?
7. **Artículos sin venta en 7 días:** ¿se muestran igual, o se ocultan por
   defecto con un check para verlos?
8. **Proveedores a excluir:** UNIFICADOR_STOCK excluye BIGAR SA y MOLINOS RIO
   DE LA PLATA S.A. por pedido puntual del usuario — no aplica a bebidas.
   ¿Hay algún proveedor de bebidas que deba excluirse de entrada?
