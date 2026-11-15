import pandas as pd

VARIABLES = {
    "frecuencia_cardiaca": ("Frecuencia cardiaca", "lpm"),
    "sueno_horas": ("Sueño", "h"),
    "actividad_min": ("Actividad física", "min"),
    "spo2": ("Oxigenación (SpO₂)", "%"),
    "temperatura_c": ("Temperatura", "°C"),
}
ESCALA_MIN = {"spo2": 0.8, "temperatura_c": 0.2}
RANGO_DELTA = {"frecuencia_cardiaca": 30.0, "sueno_horas": 30.0, "actividad_min": 30.0, "spo2": 8.0, "temperatura_c": 2.0}
UMBRAL_Z = 2.5
PERSISTENCIA = 2
DIAS_BASE = 7


def cargar(ruta):
    df = pd.read_csv(ruta, parse_dates=["timestamp"])
    return df


def diario(df):
    ok = df[df.quality_flag == "ok"].copy()
    ok["dia"] = ok.timestamp.dt.normalize()
    g = ok.groupby(["variable", "dia"]).value.median().reset_index()
    return g


def linea_base(dia_df, dias_base=DIAS_BASE):
    base = {}
    for var, s in dia_df.groupby("variable"):
        s = s.sort_values("dia")
        ref = s.head(dias_base).value
        med = ref.median()
        mad = (ref - med).abs().median()
        piso = ESCALA_MIN.get(var, 0.03 * abs(med))
        escala = max(1.4826 * mad, piso)
        base[var] = {"mediana": float(med), "mad": float(mad), "escala": float(escala),
                     "n_dias": int(len(ref)),
                     "inicio": s.dia.iloc[0], "fin": s.dia.iloc[min(dias_base, len(s)) - 1]}
    return base


def con_z(dia_df, base):
    d = dia_df.copy()
    d["z"] = d.apply(lambda r: (r.value - base[r.variable]["mediana"]) / base[r.variable]["escala"]
                     if r.variable in base else 0.0, axis=1)
    return d


def alertas(dia_df, base, umbral=UMBRAL_Z, persistencia=PERSISTENCIA):
    d = con_z(dia_df, base)
    salida = []
    for var, s in d.groupby("variable"):
        s = s.sort_values("dia").reset_index(drop=True)
        fuera = s.z.abs() >= umbral
        i = 0
        while i < len(s):
            if fuera[i]:
                j = i
                while j + 1 < len(s) and fuera[j + 1] and (s.z[j + 1] > 0) == (s.z[i] > 0):
                    j += 1
                if j - i + 1 >= persistencia:
                    tramo = s.iloc[i:j + 1]
                    nombre, unidad = VARIABLES.get(var, (var, ""))
                    sube = tramo.z.mean() > 0
                    b = base[var]
                    salida.append({
                        "variable": var, "nombre": nombre, "unidad": unidad,
                        "desde": tramo.dia.iloc[0], "hasta": tramo.dia.iloc[-1],
                        "dias": len(tramo), "z_max": float(tramo.z.abs().max()),
                        "direccion": "por encima" if sube else "por debajo",
                        "valor_ultimo": float(tramo.value.iloc[-1]),
                        "mediana_base": b["mediana"],
                        "regla": f"|z robusto| ≥ {umbral} durante ≥ {persistencia} días consecutivos",
                    })
                i = j + 1
            else:
                i += 1
    return salida


def aplicar_escenario(dia_df, variable, delta, ultimos_dias):
    d = dia_df.copy()
    if delta == 0 or ultimos_dias <= 0:
        return d
    ult = sorted(d.dia.unique())[-ultimos_dias:]
    m = (d.variable == variable) & (d.dia.isin(ult))
    d.loc[m, "value"] = d.loc[m, "value"] + delta
    return d


def calidad(df):
    return float((df.quality_flag == "ok").mean())


AMORT = 0.85
LIMITES = {"frecuencia_cardiaca": (35, 200), "sueno_horas": (0, 12), "actividad_min": (0, 300),
           "spo2": (70, 100), "temperatura_c": (34, 41)}


ENTORNOS = {
    "tendencia": "Seguir la tendencia de los últimos días",
    "orbita": "En órbita (microgravedad)",
    "regreso": "Regreso a la gravedad (aterrizaje)",
}
AUMENTO_ATERRIZAJE = 0.38
DIAS_RECUPERACION = 8
BAJA_ORBITA = 3.0


def pulso_entorno(mediana_tierra, entorno, k):
    if entorno == "orbita":
        return mediana_tierra - BAJA_ORBITA
    if entorno == "regreso":
        return mediana_tierra * (1 + AUMENTO_ATERRIZAJE * max(0.0, 1 - (k - 1) / DIAS_RECUPERACION))
    return None


def proyectar(dia_df, base, variable, horizonte=7, ventana=7, entorno="tendencia"):
    import numpy as np
    s = dia_df[dia_df.variable == variable].sort_values("dia").tail(ventana)
    if len(s) < 4:
        return None
    x = np.arange(len(s), dtype=float)
    y = s.value.to_numpy(dtype=float)
    pend = [(y[j] - y[i]) / (x[j] - x[i]) for i in range(len(y)) for j in range(i + 1, len(y))]
    m = float(np.median(pend))
    b0 = float(np.median(y - m * x))
    res = y - (b0 + m * x)
    sd = max(1.4826 * float(np.median(np.abs(res - np.median(res)))), 0.5 * base[variable]["escala"])
    n, xb = len(x), float(x.mean())
    sxx = float(((x - xb) ** 2).sum())
    ult = s.dia.iloc[-1]
    filas = []
    for k in range(1, horizonte + 1):
        xk = n - 1 + k
        centro = b0 + m * (n - 1) + m * sum(AMORT ** i for i in range(1, k + 1))
        lo_f, hi_f = LIMITES.get(variable, (-1e9, 1e9))
        centro = min(max(centro, lo_f), hi_f)
        ancho = 1.96 * sd * (1 + 1 / n + (xk - xb) ** 2 / sxx) ** 0.5
        if variable == "frecuencia_cardiaca" and entorno in ("orbita", "regreso"):
            centro = pulso_entorno(base[variable]["mediana"], entorno, k)
        z = (centro - base[variable]["mediana"]) / base[variable]["escala"]
        filas.append({"k": k, "dia": ult + pd.Timedelta(days=k), "value": centro,
                      "lo": centro - ancho, "hi": centro + ancho, "z": z})
    proy = pd.DataFrame(filas)
    alerta_dia = _primera_alerta(proy)
    return {"proy": proy, "pendiente": m, "alerta": alerta_dia, "ultimo": ult}


def _primera_alerta(proy):
    fuera = (proy.z.abs() >= UMBRAL_Z).to_numpy()
    for i in range(len(proy) - PERSISTENCIA + 1):
        tramo = proy.z.iloc[i:i + PERSISTENCIA]
        if fuera[i:i + PERSISTENCIA].all() and ((tramo > 0).all() or (tramo <= 0).all()):
            return proy.iloc[i]
    return None


SITUACIONES = {
    "despegue": {
        "nombre": "Despegue",
        "hr_min": 88, "hr_media": 99, "hr_pico": 110,
        "texto": "Pulso máximo de los tres astronautas del Apolo 11 en el despegue: 88, 99 y 110 lpm.",
        "fuente": "Apollo 11 Mission Report, Biomedical Evaluation (NASA)",
    },
    "eva": {
        "nombre": "Caminata espacial (EVA)",
        "hr_min": 88, "hr_media": 99, "hr_pico": 160,
        "texto": "Apolo 11 en la superficie lunar: promedio de 88 a 110 lpm y un máximo cercano a 160 lpm. "
                 "En Gemini XII la NASA avisaba a la tripulación si el pulso se mantenía en 140 lpm o más.",
        "fuente": "Apollo 11 Mission Report; NASA NTRS 20120003917 (Apollo 14, Gemini XII)",
    },
    "ejercicio": {
        "nombre": "Ejercicio a bordo (ISS)",
        "hr_min": 120, "hr_media": 145, "hr_pico": 163,
        "texto": "En la ISS el pulso máximo de las sesiones fue de 162 lpm en la caminadora y 163 lpm en la bicicleta; "
                 "la NASA prescribe entrenar entre 70 % y 90 % del pulso máximo. El promedio de la sesión es una estimación.",
        "fuente": "NASA/SP-2025-0273, Table 7 (rangos 120-145 son supuestos propios)",
    },
    "sueno_iss": {
        "nombre": "Dormir como en la ISS",
        "sueno": 6.1,
        "texto": "Los astronautas durmieron 6.1 h por noche en la ISS (5.96 h en el Transbordador), aunque la NASA programa 8.5 h.",
        "fuente": "Barger et al., Lancet Neurology 2014 (21 astronautas en la ISS)",
    },
}


def aplicar_situacion(res, base, variable, situacion, dia_evento):
    s = SITUACIONES.get(situacion)
    if s is None or res is None:
        return res
    proy = res["proy"].copy()
    b = base[variable]
    if variable == "frecuencia_cardiaca" and "hr_media" in s:
        i = proy.index[proy.k == dia_evento]
        if len(i):
            proy.loc[i, ["value", "lo", "hi"]] = [s["hr_media"], s["hr_min"], s["hr_pico"]]
    elif variable == "sueno_horas" and "sueno" in s:
        m = proy.k >= dia_evento
        proy.loc[m, "value"] = s["sueno"]
        proy.loc[m, "lo"] = s["sueno"] - 1.0
        proy.loc[m, "hi"] = s["sueno"] + 1.0
    proy["z"] = (proy.value - b["mediana"]) / b["escala"]
    out = dict(res); out["proy"] = proy; out["alerta"] = _primera_alerta(proy)
    return out


MALESTARES = {
    ("frecuencia_cardiaca", True): "Pulso más alto de lo normal: podría sentir cansancio, palpitaciones o estrés.",
    ("frecuencia_cardiaca", False): "Pulso más bajo de lo normal: podría sentir mareo o debilidad.",
    ("sueno_horas", False): "Duerme menos de lo normal: podría tener fatiga y dificultad para concentrarse.",
    ("sueno_horas", True): "Duerme más de lo normal: podría ser señal de agotamiento acumulado.",
    ("actividad_min", False): "Se mueve menos de lo normal: podría perder condición física.",
    ("actividad_min", True): "Se mueve más de lo normal: podría acumular fatiga muscular.",
    ("spo2", False): "Menos oxígeno en sangre de lo normal: podría sentir falta de aire, mareo o dolor de cabeza (riesgo de hipoxia).",
    ("spo2", True): "Oxigenación por encima de lo normal: no suele ser un problema; conviene revisar que el sensor esté bien colocado.",
    ("temperatura_c", True): "Temperatura más alta de lo normal: podría tener fiebre, estrés por calor o fatiga.",
    ("temperatura_c", False): "Temperatura más baja de lo normal: podría tener frío o mala regulación térmica.",
}


MALESTARES_ENTORNO = {
    ("frecuencia_cardiaca", "regreso"): "Al volver a la gravedad el pulso sube al ponerse de pie: podría marearse o, en casos como el de la NASA, desmayarse.",
    ("frecuencia_cardiaca", "orbita"): "En órbita el pulso de reposo baja un poco: es lo esperado, no es una falla.",
}
