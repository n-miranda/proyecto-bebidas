"""Funcion serverless de Vercel: equivalente a GET /api/meta en la app local
(src/web/app.py) -- meta + inconsistencias del snapshot publicado, mas los
umbrales de semaforo que vienen de config/config.json (se leen de ahi para
no duplicar el numero a mano en dos lugares)."""
import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA_SNAPSHOT = RAIZ / "data" / "snapshot.json"
RUTA_CONFIG = RAIZ / "config" / "config.json"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            snapshot = json.loads(RUTA_SNAPSHOT.read_text(encoding="utf-8"))
            config = json.loads(RUTA_CONFIG.read_text(encoding="utf-8"))
            umbrales = config["semaforo_dias_stock"]
            cuerpo = json.dumps({
                "meta": snapshot["meta"],
                "inconsistencias": snapshot["inconsistencias"],
                "umbrales_semaforo": {
                    "rojo_hasta": umbrales["rojo_hasta"],
                    "amarillo_hasta": umbrales["amarillo_hasta"],
                    "verde_hasta": umbrales["verde_hasta"],
                },
            }).encode("utf-8")
            self.send_response(200)
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
            cuerpo = json.dumps({"error": f"No se pudo leer el snapshot publicado: {exc}"}).encode("utf-8")
            self.send_response(500)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "public, max-age=0, must-revalidate")
        self.end_headers()
        self.wfile.write(cuerpo)
