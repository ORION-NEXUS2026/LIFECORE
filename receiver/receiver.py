import csv, json, os, random, sys, threading, time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PUERTO = 8000
ARCHIVO = Path(__file__).resolve().parent.parent / "data" / "sensor_log.csv"
CAMPOS = ["subject_id", "timestamp", "variable", "value", "unit", "source", "quality_flag"]
FUENTE = "sensor_wifi_XD58C"

lock = threading.Lock()
estado = {"seq": 0, "bpm": None, "calidad": "ok", "recibido": 0.0, "recientes": []}
anterior = [None]


def calidad_de(bpm):
    if bpm < 45 or bpm > 160:
        return "baja"
    if anterior[0] is not None and abs(bpm - anterior[0]) > 25:
        return "baja"
    return "ok"


def registrar(bpm):
    with lock:
        cal = calidad_de(bpm)
        anterior[0] = bpm
        estado["seq"] += 1
        estado["bpm"], estado["calidad"], estado["recibido"] = bpm, cal, time.time()
        if cal == "ok":
            estado["recientes"] = (estado["recientes"] + [bpm])[-30:]
        ARCHIVO.parent.mkdir(parents=True, exist_ok=True)
        nuevo = not ARCHIVO.exists()
        with open(ARCHIVO, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if nuevo:
                w.writerow(CAMPOS)
            w.writerow(["AST-001", datetime.now().isoformat(timespec="seconds"), "frecuencia_cardiaca",
                        bpm, "bpm", FUENTE, cal])
    print(bpm, cal)


class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, obj, code=200):
        cuerpo = json.dumps(obj).encode()
        self.send_response(code); self._cors()
        self.send_header("Content-Type", "application/json"); self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(cuerpo))); self.end_headers(); self.wfile.write(cuerpo)

    def do_OPTIONS(self):
        self.send_response(204); self._cors(); self.end_headers()

    def do_GET(self):
        if self.path.startswith("/estado"):
            with lock:
                self._json({"seq": estado["seq"], "bpm": estado["bpm"], "calidad": estado["calidad"],
                            "edad_s": (time.time() - estado["recibido"]) if estado["recibido"] else None,
                            "recientes": estado["recientes"]})
        else:
            self._json({"ok": True, "uso": "POST /latido {bpm}; GET /estado"})

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            datos = json.loads(self.rfile.read(n) or b"{}")
            bpm = int(round(float(datos["bpm"])))
            if not 20 <= bpm <= 250:
                raise ValueError("bpm fuera de rango")
        except Exception as e:
            return self._json({"error": str(e)}, 400)
        registrar(bpm)
        self._json({"ok": True})

    def log_message(self, *a):
        pass


def simular():
    bpm = 72.0
    while True:
        bpm += random.uniform(-2, 2) + (72 - bpm) * 0.1
        registrar(int(round(bpm)))
        time.sleep(60 / bpm)


if __name__ == "__main__":
    if "--simular" in sys.argv:
        threading.Thread(target=simular, daemon=True).start()
    print(f"Receptor activo en http://0.0.0.0:{PUERTO}  (Ctrl+C para detener)")
    try:
        ThreadingHTTPServer(("0.0.0.0", PUERTO), H).serve_forever()
    except KeyboardInterrupt:
        print("Detenido")
