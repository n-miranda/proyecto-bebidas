# Unificador de Stock — Bebidas

Aplicación web **local y de solo lectura** que unifica en una sola vista el
stock de bebidas de varios depósitos y muestra, por artículo, cuántos días de
venta cubre ese stock. Sirve para detectar de un vistazo qué está por quebrar y
qué está sobrestockeado, sin cruzar planillas a mano.

- **Local:** Flask + HTML/CSS/JS vanilla (sin build, sin Node).
- **Publicado:** sitio estático en Vercel con una foto fija de los datos.
- **Reglas del proyecto y especificación completa:** [`CLAUDE.md`](CLAUDE.md).

> Este proyecto nació como copia de `D:\UNIFICADOR_STOCK` (Total
> Refrigerados). La migración a datos propios de bebidas está **a medias**:
> ver [Estado de los datos](#estado-de-los-datos).

## Uso

```
pip install -r requirements.txt
python -m src.main
```

Procesa las fuentes, genera `salida\snapshot.json` y levanta
`http://127.0.0.1:5000/`. El botón **Actualizar datos** del encabezado vuelve a
leer los Excel sin reiniciar el servidor. Flask tiene `TEMPLATES_AUTO_RELOAD`
activado (`src\web\app.py`), así que un cambio en cualquier plantilla `.html`
se ve con solo recargar (Ctrl+F5) — no hace falta reiniciar el proceso.

## Estado de los datos

| Fuente | Origen | Estado |
|---|---|---|
| **Stock** | `stock_bebidas.xlsx` (pestañas OB, SV, PR, TC: una por depósito) | **Real de bebidas.** Se toma el bloque "DISPONIBLE" (columnas A-D); el bloque "FÍSICO" no se usa |
| **Venta promedio por bulto** | Columna K ("Venta Prom Pedido") de esas mismas pestañas, cruzada por la columna L ("Cod") | **Real de bebidas.** Es la base del cálculo de días de stock |
| **Tránsito** | `TRANSITO\<DEPÓSITO> - Pedidos.xlsx` + `INGRESOS.xlsx` + parsers de Posadas | Por depósito; los parsers de Posadas (Georgalos, La Serenísima, Piamontesa, Timbo, Trigos Argentinos) son de Total Refrigerados |
| **Novedades** | `TRANSITO\Novedades.xlsx` | Nota libre por artículo (hoy 6) |
| **Ventas** | `VENTAS\VENTAS.xlsx` | Heredado de Total Refrigerados; no comparte códigos con bebidas |
| **Maestro de productos** | proveedor / rubro / unidades por bulto | Heredado de Total Refrigerados; no comparte códigos con bebidas |

Las rutas salen de `config\config.json` (`rutas.*`). Consecuencias esperables,
avisadas en la propia web (chip **"N avisos"**):

- Todos los artículos figuran **SIN CLASIFICAR** (sin proveedor ni rubro) y con
  1 unidad por bulto, porque el maestro no tiene los códigos de bebidas.
- **"Venta 7d" sale en 0** casi siempre (no hay match de códigos con
  `VENTAS.xlsx`). **No afecta los días de stock**, que usan la venta promedio
  del propio archivo de stock.
- El universo de artículos es **únicamente** el de `stock_bebidas.xlsx`: no se
  agregan artículos huérfanos de ventas o tránsito.
- El filtro **Clúster** está armado pero sin datos (esperando una fuente real).
- El encabezado dice "833 artículos, 862 sin clasificar": las 862 son
  *inconsistencias* (359 códigos distintos, algunos con varios motivos, 29 ni
  están en la tabla), no artículos.

## La web

### Vista principal (`/`)

- **Encabezado** (rediseño 2026-09-23, tarjeta flotante azul de marca): logo
  real de Total, título, subtítulo "Bebidas", fecha de actualización, ventana
  de días de venta usada, chip de avisos (panel flotante que se cierra con
  clic afuera o Escape) y botón "Actualizar datos" — más, en su propia fila,
  las acciones de la tabla: "Solo sin clasificar" y exportar a PDF/Excel.
  Tipografías Poppins (título) e Inter (el resto), solo para este bloque; el
  resto de la página sigue con IBM Plex Sans/Space Grotesk.
- **Selector de vista** ("Por depósito" / "Resumen por código") y **filtros**
  (Depósito, Clúster, búsqueda por código/descripción, columnas visibles):
  van pegados justo arriba de los encabezados de columna de la tabla, no en el
  encabezado azul. Los filtros son combinables y en vivo; los activos se ven
  como chips con "Limpiar todo" arriba de las tarjetas.
- **Tarjetas:** artículos filtrados, riesgo de quiebre, normal y sobrestock.
  Cada una es clickeable y filtra la tabla por estado (si se está en "Resumen
  por código", el click vuelve primero a "Por depósito"). Los textos de
  detalle ("Menos de 3 días", etc.) salen de la configuración. Las categorías
  suman el total: **rojo + atención + normal + sobrestock + sin venta** (la de
  "atención" no tiene tarjeta; su cantidad se ve en el detalle de "Riesgo de
  quiebre" y "sin venta" en el de "Artículos filtrados").
- **Tabla "Por depósito"**, de una sola hoja (sin paginar), con encabezado fijo
  y scroll propio. Columnas: estado, código, descripción, depósito, stock
  (bultos, sin decimales), venta promedio (bultos), días de stock, tránsito
  (bultos, sin decimales) y días de stock con tránsito. La novedad, si existe,
  se ve bajo la descripción.
- **Tabla "Resumen por código"**: la misma tabla cambia a una fila por código
  con una columna de stock por depósito (antes era la página aparte
  `/stock-general`, hoy vive acá como una 2ª vista — ver más abajo). El stock
  de cada celda se pinta con el mismo semáforo que "Por depósito", y al pasar
  el cursor muestra el tránsito de ese depósito si tiene.
- **Pie:** cantidad filtrada y proveedor con más artículos en riesgo.

### Arranque y orden

- **La web arranca sin orden ni filtros activos.** La tabla muestra el orden de
  origen (por depósito y código).
- Cada clic en un encabezado recorre **ascendente → descendente → sin orden**
  (de A a Z / de Z a A en las columnas de texto). Al pasar a otra columna, la
  anterior se limpia. El tooltip del encabezado indica qué hace el próximo clic.
- Los artículos sin dato de días de stock (`S/V`, `—`) quedan siempre al final.

### Semáforo (sobre "días de stock")

| Estado | Regla | Significado |
|---|---|---|
| Rojo | menos de 3 días | Riesgo de quiebre |
| Amarillo | 3 a 7 días | Atención |
| Verde | 7 a 20 días | Normal |
| Sobrestock | más de 20 días | Exceso |
| Neutro | sin venta | `S/V` (hay stock) o `—` (sin stock ni venta) |

Umbrales en `config\config.json` → `semaforo_dias_stock`. Cuando un artículo
tiene stock de seguridad conocido, el corte es relativo a ese valor
(`semaforo_relativo_stock_seguridad`). El estado nunca depende solo del color:
el punto lleva texto para lectores de pantalla y el valor va en negrita.

**Quiebre cubierto:** una fila en rojo con tránsito se marca con `▶` en la
columna Tránsito (el quiebre está cubierto por mercadería en camino). Sin marca
es un quiebre real.

### Resumen por código

Una fila por código y **una columna por depósito**, más tránsito total y
novedad. Buscador, encabezados ordenables con el mismo ciclo de tres estados, y
**Exportar a Excel** que respeta el orden y la búsqueda que se ven en pantalla.
Es la 2ª vista de la tabla principal (pestaña "Resumen por código", ver
arriba); comparte los datos ya cargados, sin pedirlos de nuevo al servidor.

**`/stock-general` (standalone, legacy):** la página aparte que existía antes
de fusionar esta vista al dashboard principal. Sigue funcionando igual (mismo
componente, mismo `stock_general.js`), pero ya nada del dashboard la enlaza —
solo queda accesible tecleando la URL a mano.

### Exportar

- **Excel:** genera un CSV con `;` y BOM UTF-8, que Excel en configuración
  regional argentina abre directo. Exporta lo filtrado y ordenado en pantalla.
- **PDF:** usa la impresión del navegador. Sale en **A4 horizontal** (se puede
  cambiar en el diálogo), con encabezado que incluye el **logo de Total**, la
  fecha del corte y los filtros aplicados. En papel las descripciones pasan a
  otra línea y las cifras no se recortan; el encabezado se repite en cada
  página y las filas no se parten.

### Formato

Decimales con coma y miles con punto (`1.234,56`), fechas `DD/MM/AAAA`. Días de
stock con 1 decimal; **stock y tránsito en bultos enteros, sin decimales**
(venta promedio sigue con 2, es un promedio). Las animaciones (conteo de
tarjetas, entrada de filas) se desactivan con `prefers-reduced-motion`.

## Identidad visual

Rediseño **"Tablero de stock"**: fondo off-white `#f5f4f0`, azul `#2e5e7e`
como único color de acción fuera del encabezado; rojo, verde y ámbar
reservados al semáforo. Tipografías IBM Plex Sans y Space Grotesk (Google
Fonts, con fallback a las del sistema) para el cuerpo de la página.

**Encabezado** (rediseño 2026-09-23, ver
`rediseno-encabezado-unificador-stock_1.md`): tarjeta flotante azul de marca
(`#2E4FE0`, `border-radius: 32px` antes de los dos achiques posteriores),
distinta del resto de la paleta — es un cambio de piel escopeado solo a ese
componente, no una retematización global. Tipografías Poppins (título) e
Inter (chips/botones/filtros), solo ahí. El **logo real de Total**
(`logo_total.jpg`) vive en el encabezado, no un ícono de texto; también
aparece en el encabezado del PDF exportado. La página `/stock-general`
(standalone, legacy) no tiene este rediseño: sigue con la barra superior
oscura original.

La paleta Quilmes usada el 2026-09-18 ya no está vigente (queda en el
historial de git, commit `f17d333`).

## Configuración

Todo número de negocio y toda ruta salen de `config\config.json`: rutas de
origen, ventana de días de venta, `incluir_dia_actual`, umbrales del semáforo,
días de vencimiento de pedidos pendientes y `proveedores_excluidos` (BIGAR SA y
Molinos Río de la Plata, heredados de Total Refrigerados). Los feriados están
en `config\feriados.json` (no hardcodeados en el código; falla con un error
claro si falta el año).

## Tests

```
python -m unittest discover -s src/tests -t . -v
```

Cubren el calendario (días de venta y feriados), la conversión a bultos y los
casos borde de días de stock, y el tránsito.

## Sitio publicado (Vercel) — solo lectura

Versión de esta web publicada en Vercel para consultarla sin tener la app local
corriendo: <https://proyecto-bebidas-rose.vercel.app>. **No procesa Excel en la
nube** (Vercel no tiene acceso al disco de esta PC): muestra una foto fija de
`data\snapshot.json`, publicada a mano.

- `public\` — copia estática de `src\web\templates` / `src\web\static`. **No es
  idéntica:** no tiene el botón "Actualizar datos" (queda una etiqueta "Solo
  lectura" en su lugar) y usa rutas `/static/…` en vez de Jinja. El resto —
  incluido "Resumen por código" como 2ª vista de `index.html`, y la página
  standalone `stock-general.html` — es igual a `src\web\`.
- `api\stock.py`, `api\meta.py` — funciones serverless de Vercel (Python, sin
  Flask; `vercel.json` fija `"framework": null` a propósito) con la misma forma
  que `GET /api/stock` y `GET /api/meta` de la app local. `api\meta.py` también
  devuelve los umbrales del semáforo leídos de `config\config.json`.
- `data\snapshot.json` — la foto fija publicada; copia manual de
  `salida\snapshot.json`, no se regenera sola.
- `.vercelignore` excluye `src\`, `STOCK\`, `VENTAS\`, `TRANSITO\`, `logs\` y
  `salida\`. Un archivo suelto en `src\` confundía al detector de funciones de
  Vercel.
- `STOCK\`, `VENTAS\`, `TRANSITO\`, `salida\` y `logs\` **no se suben** al repo
  (`.gitignore`). **El repo es público:** nunca subir los Excel de origen.

### Publicar datos nuevos

1. `python -m src.main` para regenerar `salida\snapshot.json` con los Excel del
   día.
2. Copiar ese archivo a `data\snapshot.json`.
3. `git add data\snapshot.json && git commit -m "Actualizar snapshot publicado" && git push`
   — Vercel redespliega solo al detectar el push.

### Publicar cambios de diseño o de código

Un cambio en `src\web\` **no alcanza**: hay que replicarlo en `public\`.

1. Editar `src\web\*` y probarlo local con `python -m src.main`.
2. Replicarlo en `public\*`. No copiar encima (se perderían las diferencias de
   arriba): usar un **merge de 3 vías**, con la última versión publicada como
   base:
   `git merge-file public/X <(git show HEAD:src/web/X) src/web/X`
   y resolver a mano los conflictos.
3. Probar `public\` tal cual (con un servidor que sirva la carpeta y los
   handlers de `api\`) antes de subir.
4. `git add` **solo los archivos del cambio** y revisar `git diff --cached`
   antes del push, para que no se cuele algo sin aprobar.
5. `git push` y confirmar contra la URL de producción en vez de asumir que el
   build salió bien.

Los cambios grandes de estética se prueban **primero solo en local** y se suben
cuando se aprueban; los arreglos de datos o bugs se suben directo.

## Cuándo pasar a datos propios de bebidas

Cuando estén las fuentes reales de ventas, tránsito y maestro de bebidas (o la
API de Chess):

1. Ejecutar el **Paso 0 — Reconocimiento** (`CLAUDE.md`, sección 12) contra esos
   archivos: no asumir que comparten formato con Total Refrigerados.
2. Reescribir `config\mapeo_columnas.json` con el mapeo confirmado.
3. Actualizar `config\config.json` (rutas, `proveedores_excluidos`,
   `semaforo_relativo_stock_seguridad`).
4. Definir si aplican los parsers de `src\fuentes\pedidos_posadas\` o si hacen
   falta parsers nuevos.
5. Responder las preguntas abiertas de `CLAUDE.md` (sección 13).

Las fuentes están detrás de las interfaces de `src\fuentes\base.py`: pasar de
Excel a un servidor compartido (ruta de red UNC en `config.json`) o a la API de
Chess implica escribir un adaptador nuevo que devuelva las mismas columnas. Hoy
el consolidador instancia las clases Excel directamente
(`src\consolidador.py`); para elegir la fuente desde `config.json` falta una
pequeña fábrica. Las credenciales de una API van en variables de entorno o en
un archivo local ignorado por git, nunca en el repo.

## Pendientes conocidos

- Agrupar visualmente los artículos que están en más de un depósito (hoy
  aparecen en filas separadas, una por depósito).
- Reemplazar el maestro de productos y las ventas por los de bebidas: hoy todo
  figura "SIN CLASIFICAR".
- Aclarar el texto del encabezado ("862 sin clasificar" cuenta inconsistencias,
  no artículos).
- `actualizar.bat` (previsto en `CLAUDE.md`) todavía no existe: se arranca con
  `python -m src.main`.
- Proyecto Vercel duplicado `proyecto-bebidas-ui7q`, sin resolver.
- La página standalone `/stock-general` quedó sin uso desde que "Resumen por
  código" se fusionó al dashboard principal; se podría borrar si no hace
  falta mantener el link viejo.

## Historial de cambios

**2026-09-23**
- Rediseño del encabezado (`rediseno-encabezado-unificador-stock_1.md`):
  tarjeta flotante azul, tipografías Poppins/Inter, logo real conservado.
  Reducido ~40% en dos rondas después de la primera versión. Vista+filtros y
  el bloque de exportar/"solo sin clasificar" intercambiaron posición: los
  primeros quedaron pegados arriba de los encabezados de columna; el segundo
  pasó al encabezado azul. Logo agrandado 35% sobre el tamaño reducido.
- "Resumen por código" pasa de página aparte (`/stock-general`, en otra
  pestaña) a ser la 2ª vista de la misma tabla del dashboard principal, con
  semáforo por celda y tooltip de tránsito por depósito. `/stock-general`
  standalone se deja intacta pero sin uso.
- Stock y tránsito se muestran en bultos enteros, sin decimales.
- `TEMPLATES_AUTO_RELOAD` activado en Flask (evita servir una plantilla vieja
  junto a JS/CSS nuevos si no se reinicia el proceso).
- KPI arriba de los filtros; tarjetas KPI achicadas ~45% en total.

**2026-09-19**
- Rediseño del panel principal: sin gráficos, avisos como chip colapsable,
  tarjetas compactas, tabla de una sola hoja con encabezado fijo, novedad bajo
  la descripción y `▶` de quiebre cubierto.
- La web arranca sin orden ni filtros; orden en tres estados en ambas tablas.
- PDF en A4 horizontal, con celdas que no se cortan y anchos propios de papel.
- Botón "Stock general" con el mismo estilo que "Exportar a Excel".
- Rediseño "Tablero de stock" (reemplaza la paleta Quilmes).
- Novedades y tránsito por depósito en Stock General.

**2026-09-18**
- Stock real de bebidas desde `stock_bebidas.xlsx` (depósitos OB, SV, PR, TC) y
  venta promedio por bulto como base de los días de stock.
- El universo de artículos pasa a ser solo el del stock de bebidas.
- Se quita el filtro/tarjeta de "Atención"; columnas que se ajustan al dato más
  largo.
- Exportar a Excel en Stock General; encabezado del PDF con filtros aplicados y
  logo de Total.
- Paleta Quilmes, columnas seleccionables, gráficos y transiciones (luego
  reemplazados).

**2026-09-17**
- Versión inicial (copia de UNIFICADOR_STOCK) y publicación de solo lectura en
  Vercel (`framework: null`, `.vercelignore`).
- Se quita la columna "Venta 7d"; el filtro de Rubro pasa a Clúster (sin datos
  por ahora).
