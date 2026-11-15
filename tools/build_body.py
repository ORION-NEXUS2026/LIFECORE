"""Extracts the structures used by the hologram from the BodyParts3D atlas and writes a compact binary format.

Source: BodyParts3D (CC BY 4.0, DBCLS) via github.com/slorksmo/human-atlas (MIT).
Usage: python tools/build_body.py <atlas_models_dir> <output_dir> <heart_provenance_json>
Output: body.json + body.bin (put them in app/static/hologram/). Structures that already belong to the heart model are skipped.
Genital structures are excluded on purpose (not needed for the cardiovascular demo).
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

ATLAS_DIR, OUT_DIR, HEART_PROV = map(Path, sys.argv[1:4])
atlas = json.loads((ATLAS_DIR / "atlas.json").read_text())
parts = {p["id"]: p for p in atlas["parts"]}
chunks = {}


def chunk(i):
    if i not in chunks:
        chunks[i] = (ATLAS_DIR / f"body-{i}.bin").read_bytes()
    return chunks[i]


# ids ya usados por el modelo del corazón
prov = json.loads(HEART_PROV.read_text())
heart_ids = set()
def walk(o):
    if isinstance(o, dict):
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
    elif isinstance(o, str) and o.startswith("FJ"):
        heart_ids.add(o)
walk(prov)
print("elementos del corazón omitidos:", len(heart_ids))


def diag(p):
    a, b = p["bounds"]
    return float(np.linalg.norm(np.array(b) - np.array(a)))


def centre(p):
    a, b = p["bounds"]
    return [(a[i] + b[i]) / 2 for i in range(3)]


def name(p):
    return p["name"].lower()


groups = {}
GENITAL = ("penis", "testis", "scrot", "epididym", "prostate", "seminal", "spermatic", "deferens", "urethra", "cavernosum", "spongiosum", "glans", "deferent", "ductus", "pampiniform", "testic", "cremaster")


def pick(key, pred):
    groups[key] = [p for p in atlas["parts"] if p["id"] not in heart_ids and not any(k in name(p) for k in GENITAL) and pred(p)]


def aplanar_ingle(P):
    """Suaviza la piel en la región genital (se pierde esa protuberancia; el modelo queda neutro)."""
    P = P.reshape(-1, 3).copy()
    y, ax = P[:, 1], np.abs(P[:, 0])
    t = np.clip((y - 0.74) / (0.90 - 0.74), 0, 1)
    zlin = 0.035 + 0.057 * t                       # línea suave: pubis -> vientre
    w = np.clip((0.075 - ax) / 0.035, 0, 1)        # peso lateral (1 en el centro, 0 a >7.5 cm)
    w = w * w * (3 - 2 * w)
    inreg = (y > 0.70) & (y < 0.93) & (P[:, 2] > 0.0)
    P[:, 2] = np.where(inreg & (P[:, 2] > zlin), P[:, 2] * (1 - w) + zlin * w, P[:, 2])
    return P.reshape(-1)

lung_ids = set()
for c in atlas["concepts"]:
    if c["name"] in ("right lung", "left lung"):
        lung_ids.update(c["elements"])

SKIP_BONE = ("phalanx", "phalanges", "carpal", "metacarpal", "tarsal", "metatarsal", "sesamoid", "lunate", "scaphoid",
             "triquetral", "pisiform", "trapezi", "capitate", "hamate", "calcaneus", "talus", "cuboid", "cuneiform", "navicular",
             "gingiva", "tooth", "teeth", "incisor", "canine", "molar", "premolar", "ossicle", "malleus", "incus", "stapes")
VESSEL_BIG = 0.11
organ_keys = ("diaphragm", "stomach", "duodenum", "ascending colon", "transverse colon", "descending colon", "sigmoid colon",
              "rectum", "kidney", "spleen", "gallbladder", "esophagus", "pancreas", "caudate lobe of liver")

pick("skin", lambda p: p["id"] == "FJ2810")
pick("skeleton", lambda p: p["system"] == "skeletal" and not any(k in name(p) for k in SKIP_BONE))
pick("airways", lambda p: (p["id"] in lung_ids and p["system"] == "respiratory") or p["id"] in ("FJ2541",) or
     (p["system"] == "respiratory" and "bronch" in name(p)))
pick("pulmonary_vessels", lambda p: p["id"] in lung_ids and p["system"] in ("arterial", "venous"))
pick("arteries", lambda p: p["system"] == "arterial" and p["id"] not in lung_ids and diag(p) >= VESSEL_BIG)
pick("veins", lambda p: p["system"] == "venous" and p["id"] not in lung_ids and diag(p) >= VESSEL_BIG)
pick("organs", lambda p: any(k in name(p) for k in organ_keys) and p["system"] in ("digestive", "muscular", "urinary", "lymphatic"))
pick("brain", lambda p: p["system"] == "nervous" and any(k in name(p) for k in ("cerebral hemisphere", "cerebellum", "brainstem", "brain stem", "cerebrum", "hemisphere")))

OUT_DIR.mkdir(parents=True, exist_ok=True)
blob = bytearray()
manifest = {"source": "BodyParts3D 4.0 (c) DBCLS, CC BY 4.0", "units": "metres", "axes": {"x": "patient left", "y": "superior", "z": "anterior"}, "groups": {}}


def align(n):
    while len(blob) % n:
        blob.append(0)


for key, L in groups.items():
    if not L:
        print(key, "VACÍO"); continue
    P, N, I, off = [], [], [], 0
    for p in L:
        buf = chunk(p["chunk"])
        v, ic = p["vertexCount"], p["indexCount"]
        pos = np.frombuffer(buf, "<f4", v * 3, p["positions"])
        P.append(pos)
        N.append(np.frombuffer(buf, "<i2", v * 3, p["normals"]))
        I.append(np.frombuffer(buf, "<u4", ic, p["indices"]) + off)
        off += v
    P = np.concatenate(P).astype("<f4"); N = np.concatenate(N).astype("<i2"); I = np.concatenate(I).astype("<u4")
    if key == "skin":                                # sin región genital: se retiran los triángulos
        V = P.reshape(-1, 3); T = I.reshape(-1, 3); c = V[T].mean(axis=1)
        quitar = (np.abs(c[:, 0]) < 0.05) & (c[:, 1] > 0.74) & (c[:, 1] < 0.85) & (c[:, 2] > 0.0)
        print("triángulos genitales retirados:", int(quitar.sum()))
        I = T[~quitar].reshape(-1).astype("<u4")
    align(4); po = len(blob); blob += P.tobytes()
    align(4); no = len(blob); blob += N.tobytes()
    align(4); io = len(blob); blob += I.tobytes()
    manifest["groups"][key] = {"vertices": int(off), "indices": int(len(I)), "positions": po, "normals": no, "index": io,
                               "parts": len(L), "tris": int(len(I) // 3)}
    print(f"{key:18s} parts={len(L):4d} verts={off:7d} tris={len(I)//3:7d}")

(OUT_DIR / "body.bin").write_bytes(bytes(blob))
(OUT_DIR / "body.json").write_text(json.dumps(manifest))
print("body.bin MB:", round(len(blob) / 1e6, 2))
