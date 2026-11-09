"""Servidor web de OrigenChain (solo biblioteca estándar). Uso: python server.py [puerto]"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from blockchain import Cadena, ErrorNegocio, FLUJO
import qr

AQUI = os.path.dirname(os.path.abspath(__file__))
cadena = Cadena(os.path.join(AQUI, "cadena.json"))
cadena.sembrar()
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


class H(BaseHTTPRequestHandler):
    def _enviar(self, codigo, cuerpo, tipo="application/json"):
        if not isinstance(cuerpo, (bytes, str)):
            cuerpo = json.dumps(cuerpo, ensure_ascii=False)
        if isinstance(cuerpo, str):
            cuerpo = cuerpo.encode()
        self.send_response(codigo)
        self.send_header("Content-Type", tipo + "; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        u = urlparse(self.path)
        p = u.path.strip("/").split("/")
        if u.path == "/" or p[0] == "t":
            return self._enviar(200, open(os.path.join(AQUI, "static", "index.html"), "rb").read(), "text/html")
        if p[:2] == ["api", "resumen"]:
            return self._enviar(200, cadena.resumen())
        if p[:2] == ["api", "lotes"] and len(p) == 2:
            return self._enviar(200, cadena.lotes(parse_qs(u.query).get("q", [""])[0]))
        if p[:2] == ["api", "lotes"] and len(p) == 3:
            ev = cadena.eventos(p[2])
            if not ev:
                return self._enviar(404, {"error": "Lote no encontrado"})
            return self._enviar(200, {"lote": cadena.lotes(p[2])[0], "eventos": ev, "flujo": FLUJO})
        if p[:2] == ["api", "cadena"]:
            return self._enviar(200, {"bloques": cadena.bloques, **cadena.verificar()})
        if p[:2] == ["api", "qr"] and len(p) == 3:
            host = self.headers.get("Host", f"localhost:{PUERTO}")
            return self._enviar(200, qr.svg(f"http://{host}/t/{p[2]}"), "image/svg+xml")
        self._enviar(404, {"error": "No encontrado"})

    def do_POST(self):
        p = urlparse(self.path).path.strip("/").split("/")
        try:
            d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or "{}")
            if p == ["api", "lotes"]:
                return self._enviar(201, cadena.registrar_lote(d.pop("actor", ""), d))
            if len(p) == 4 and p[:2] == ["api", "lotes"] and p[3] == "eventos":
                return self._enviar(201, cadena.registrar_evento(p[2], d.get("evento"), d.get("actor", ""), {"nota": d.get("nota", "")}))
            self._enviar(404, {"error": "No encontrado"})
        except (ErrorNegocio, ValueError, KeyError) as e:
            self._enviar(400, {"error": str(e)})

    def log_message(self, *a):
        pass


class Servidor(ThreadingHTTPServer):
    allow_reuse_address = False  # evita compartir puerto con otro programa (p. ej. en Windows)


if __name__ == "__main__":
    import webbrowser
    for puerto in range(PUERTO, PUERTO + 20):
        try:
            srv = Servidor(("127.0.0.1", puerto), H)
            break
        except OSError:
            print(f"Puerto {puerto} ocupado, probando el siguiente...")
    else:
        sys.exit("No se encontró un puerto libre")
    url = f"http://localhost:{puerto}"
    print(f"OrigenChain en {url}  (Ctrl+C para detener)")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    srv.serve_forever()
