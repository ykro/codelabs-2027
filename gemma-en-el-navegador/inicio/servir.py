# Sirve esta carpeta en http://localhost:8000 sin caché, para que cada recarga
# de Chrome use la última versión de tus archivos.
#   python3 servir.py
import http.server


class SinCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


print("Sirviendo en http://localhost:8000 (Ctrl+C para detener)", flush=True)
http.server.ThreadingHTTPServer(("localhost", 8000), SinCache).serve_forever()
