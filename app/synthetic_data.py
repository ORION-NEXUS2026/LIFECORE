"""Synthetic data generator for the fictional astronaut AST-001 (NOT real measurements).

14-day mission: days 1-7 are the reference period (the astronaut's normal); from day 8 the heart rate rises
and sleep drops gradually, so the hologram goes through every color: gray (one low day), blue, yellow,
orange and red (>= 114 bpm). Color ranges come from NASA and Mayo Clinic values (see docs/nasa-references.md).
"""
import numpy as np
import pandas as pd

SUJETO = "AST-001"
FUENTE = "sintetico"
INICIO = pd.Timestamp("2026-10-30")      # Oct 30 - Nov 12, 2026

# (first day, last day, name), days counted from 1
FASES = [(1, 7, "Referencia"), (8, 14, "Cambio gradual")]


def fase(d):
    """Phase name for day d (1-14)."""
    for a, b, nombre in FASES:
        if a <= d <= b:
            return nombre
    return ""


def generar(dias=14, semilla=8):
    rng = np.random.default_rng(semilla)
    filas = []
    sueno_prev = 0.0
    for i in range(dias):
        d = i + 1
        t = max(0.0, d - 8.0)                       # cambio gradual desde el día 9
        deriva = t * (1.0 + 0.03 * t)
        dia_hr = rng.normal(0, 0.9)
        bajo = -9.0 if d == 3 else 0.0              # un día de pulso bajo (gris), sin llegar a ser alerta
        for h in range(0, 24, 2):
            circ = -6 if (h < 6 or h >= 22) else (3 if 10 <= h <= 18 else 0)
            pico = rng.normal(8, 3) if rng.random() < 0.08 and 8 <= h <= 20 else 0
            hr = 66 + circ + dia_hr + bajo + pico + 7.8 * deriva + rng.normal(0, 2.0)
            if rng.random() < 0.04:
                continue
            filas.append((SUJETO, INICIO + pd.Timedelta(days=i, hours=h),
                          "frecuencia_cardiaca", round(hr, 1), "lpm", FUENTE, "ok"))
        sueno_prev = 0.35 * sueno_prev + rng.normal(0, 0.3)
        sueno = float(np.clip(7.2 - 0.42 * deriva + sueno_prev, 3.0, 9.5))
        filas.append((SUJETO, INICIO + pd.Timedelta(days=i, hours=7), "sueno_horas",
                      round(sueno, 2), "h", FUENTE, "ok"))
        act = 55 + 2.5 * np.sin(2 * np.pi * i / 3) + rng.normal(0, 3) - 1.0 * deriva
        filas.append((SUJETO, INICIO + pd.Timedelta(days=i, hours=20), "actividad_min",
                      round(float(act), 1), "min", FUENTE, "ok"))
        # SpO2 (4 readings/day): slightly lower while asleep; small dip as the change phase advances (stays within 95-100 %)
        # Temperature (4 readings/day): circadian ~0.4 C swing, tiny rise with the change phase
        dia_sp, dia_tp = rng.normal(0, 0.15), rng.normal(0, 0.08)
        for h in (2, 8, 14, 20):
            sp = 97.6 + (-0.6 if h == 2 else 0.0) + dia_sp - 0.25 * deriva + rng.normal(0, 0.35)
            filas.append((SUJETO, INICIO + pd.Timedelta(days=i, hours=h), "spo2",
                          round(float(min(sp, 100.0)), 1), "%", FUENTE, "ok"))
            tp = 36.6 + {2: -0.3, 8: -0.1, 14: 0.15, 20: 0.1}[h] + dia_tp + 0.05 * deriva + rng.normal(0, 0.08)
            filas.append((SUJETO, INICIO + pd.Timedelta(days=i, hours=h), "temperatura_c",
                          round(float(tp), 2), "°C", FUENTE, "ok"))
    # Un valor atípico marcado con calidad baja (para probar el filtrado)
    filas.append((SUJETO, INICIO + pd.Timedelta(days=4, hours=13), "frecuencia_cardiaca",
                  140.0, "lpm", FUENTE, "baja"))
    df = pd.DataFrame(filas, columns=["subject_id", "timestamp", "variable", "value",
                                      "unit", "source", "quality_flag"])
    return df.sort_values("timestamp").reset_index(drop=True)


if __name__ == "__main__":
    df = generar()
    df.to_csv("datos_sinteticos.csv", index=False)
    print(f"datos_sinteticos.csv: {len(df)} filas")
