# Unificador de Stock — Bebidas

> Este proyecto nace como copia de `D:\UNIFICADOR_STOCK` (mismo sistema,
> pensado para terminar unificando el stock de bebidas). **Por pedido del
> usuario (2026-09-17), por el momento sigue trabajando contra las mismas
> bases** (mismos archivos de STOCK, VENTAS, TRANSITO y el mismo maestro de
> productos que UNIFICADOR_STOCK) — ver la advertencia al principio de
> [`CLAUDE.md`](CLAUDE.md).

## Qué hace hoy

Es una copia funcional en paralelo de UNIFICADOR_STOCK: mismo motor de
cálculo, misma web, y corriendo contra los mismos datos reales (se copiaron
`STOCK\stock.xlsx`, `STOCK\rubros.xlsx`, `VENTAS\VENTAS.xlsx` y
`TRANSITO\INGRESOS.xlsx`). `config\config.json` y `config\mapeo_columnas.json`
son idénticos a los de UNIFICADOR_STOCK y siguen siendo válidos tal cual.

**Importante:** al ser una copia independiente, los dos proyectos ya no se
actualizan entre sí. Si se corrige algo en `D:\UNIFICADOR_STOCK` (config,
código, o se refrescan los Excel de origen), hay que replicarlo acá a mano
mientras ambos compartan las mismas bases.

## Uso

```
python -m src.main
```

Procesa las fuentes, genera `salida\snapshot.json` y levanta
`http://127.0.0.1:5000/`.

## Cuándo pasar a datos propios de bebidas

Cuando se defina la fuente real de stock/ventas/tránsito de bebidas:

1. Ejecutar el **Paso 0 — Reconocimiento** (`CLAUDE.md`, sección 12) contra
   esos archivos nuevos — no asumir que comparten formato con Total
   Refrigerados.
2. Reescribir `config\mapeo_columnas.json` con el mapeo confirmado.
3. Actualizar `config\config.json` → rutas, `proveedores_excluidos` y
   `semaforo_relativo_stock_seguridad` para bebidas.
4. Definir si aplican o no los parsers de `src\fuentes\pedidos_posadas\`
   (hoy son de proveedores de Posadas: Georgalos, La Serenisima, Piamontesa,
   Timbo, Trigos Argentinos) o si hace falta escribir parsers nuevos.
5. Responder las preguntas abiertas de `CLAUDE.md` (sección 13).

## Tests

```
python -m unittest discover -s src/tests -t . -v
```

## Sitio publicado (Vercel) — solo lectura

Hay una versión de esta web publicada en Vercel para poder consultarla sin
tener la app local corriendo. **No procesa Excel en la nube** (Vercel no
tiene acceso al disco de esta PC): muestra una foto fija de
`data\snapshot.json`, publicada a mano.

Qué es cada cosa:
- `public\` — copia estática de `src\web\templates`/`src\web\static`, sin
  Jinja y sin el botón "Actualizar datos" (no tiene sentido en la nube).
- `api\stock.py`, `api\meta.py` — funciones serverless de Vercel (Python,
  sin Flask) que sirven `data\snapshot.json` con la misma forma que
  `GET /api/stock` y `GET /api/meta` de la app local.
- `data\snapshot.json` — la foto fija publicada. Es una copia manual de
  `salida\snapshot.json`, no se regenera sola.
- `STOCK\`, `VENTAS\`, `TRANSITO\`, `salida\`, `logs\` **no se suben** al
  repo (`.gitignore`) — son datos de origen o generados en cada corrida
  local, no hace falta que estén en GitHub/Vercel.

### Para publicar datos nuevos

1. Correr `python -m src.main` (o `python -m src.snapshot`) localmente para
   regenerar `salida\snapshot.json` con los Excel del día.
2. Copiar ese archivo a `data\snapshot.json`.
3. `git add data\snapshot.json && git commit -m "Actualizar snapshot publicado" && git push`
   — Vercel redespliega solo al detectar el push (repo conectado a GitHub).
