"""Loads the 3D hologram (Three.js bundle served as a Streamlit static file).

Click the heart: zoom and focus; click outside or "Volver": go back. Drag: rotate. Wheel: zoom.
Anatomy: BodyParts3D (c) DBCLS (CC BY 4.0) via Human Atlas and heart-anatomy-lab. Schematic, not clinical.
The ECG trace is ILLUSTRATIVE (generated from the heart rate).
"""
import json
from pathlib import Path
from urllib.parse import quote

_STATIC = Path(__file__).parent / "static" / "hologram"
ATRIBUCION = ("Modelos anatómicos: BodyParts3D © DBCLS (CC BY 4.0; Mitsuhashi et al., Nucleic Acids Res 2009) "
              "vía Human Atlas y heart-anatomy-lab.")

_VERSION = int(max((f.stat().st_mtime for f in _STATIC.glob("*")), default=0))   # cache-busting


def holograma_html(bpms, estado="normal", etiqueta="AST-001", subetiqueta="Gemelo digital",
                   fuente="DATOS SINTÉTICOS", live=False, base=None):
    """Return the URL of the hologram page with its configuration in the query string."""
    bpms = [float(b) for b in bpms if b and 30 <= float(b) <= 200] or [72.0]
    bpms = bpms[-600:]
    cfg = {"bpms": bpms, "estado": "alerta" if estado == "alerta" else "normal",
           "etiqueta": etiqueta, "sub": subetiqueta, "fuente": fuente, "v": _VERSION}
    if live:                                     # live beats from receiver/receiver.py (WiFi)
        cfg["live"] = "http://localhost:8000"
        cfg["base"] = base
    return f"/app/static/hologram/index.html?v={_VERSION}&cfg=" + quote(json.dumps(cfg, ensure_ascii=False))
