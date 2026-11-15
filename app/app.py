"""Lifecore - digital twin of an astronaut's health (educational prototype).

Run from the repository root:  streamlit run app/app.py
Pages: control center, profile, current state, trends, explainable alerts, simulator, live sensor.
User-facing text is in Spanish (the team language); see docs/ for the English documentation.
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import json
import urllib.request

import streamlit as st
import streamlit.components.v1 as components

import analysis as an
from synthetic_data import fase as fase_mision
from synthetic_data import generar
from hologram import holograma_html, ATRIBUCION

BASE_DIR = Path(__file__).parent
ROOT = BASE_DIR.parent                      # repository root
DATA_DIR = ROOT / "data"
st.set_page_config(page_title="Lifecore", page_icon="🫀", layout="wide", initial_sidebar_state="expanded")

# Paleta clara con azul y rojo "institucional espacial" (solo colores; sin logotipos de ninguna agencia)
AZUL, AZUL_CL, ROJO, AMBAR, VERDE = "#0B3D91", "#1F6FD1", "#E03A1E", "#D98200", "#14935F"
CIAN = AZUL_CL          # color principal de las gráficas

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500&display=swap');
html, body, [class*="css"], .stMarkdown, p, label { font-family: 'IBM Plex Sans','Segoe UI',system-ui,sans-serif; }
.stApp { background: linear-gradient(180deg,#ffffff 0%,#f3f6fb 100%) fixed; color:#0B1F3A; }
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.4rem; max-width: 1500px; }
[data-testid="stToolbar"] { display: flex !important; }
/* el holograma ocupa casi toda la altura de la ventana (mínimo 760 px) y va enmarcado como una pantalla */
[data-testid="stIFrame"], [data-testid="stElementContainer"]:has(> [data-testid="stIFrame"]) { height: max(760px, calc(100vh - 100px)) !important; }
[data-testid="stIFrame"] { border: 2px solid #0B3D91 !important; border-radius: 14px; box-shadow: 0 10px 30px rgba(11,61,145,.22); }
[data-testid="stExpandSidebarButton"] {
  position: fixed !important; top: 12px !important; left: 12px !important; width: 42px !important; height: 42px !important;
  min-width: 42px !important; display: flex !important; align-items: center; justify-content: center;
  opacity: 1 !important; visibility: visible !important; z-index: 999999 !important; cursor: pointer;
  background: #ffffff !important; border: 1.5px solid #0B3D91 !important; border-radius: 10px !important; color: #0B3D91 !important; }
[data-testid="stExpandSidebarButton"] svg { color: #0B3D91 !important; fill: #0B3D91 !important; }
[data-testid="stSidebar"] { background: #ffffff; border-right: 3px solid #0B3D91; }
[data-testid="stSidebar"] [role="radiogroup"] label { padding: 6px 4px; }

.hdr { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px;
       padding: 6px 2px 14px; margin-bottom: 18px; border-bottom: 3px solid transparent;
       border-image: linear-gradient(90deg,#0B3D91 0%,#1F6FD1 62%,#E03A1E 100%) 1; }
.brand { font-family:'Chakra Petch',sans-serif; font-weight:700; font-size:2.1rem; letter-spacing:.06em; color:#0B3D91; line-height:1; }
.brand b { color:#E03A1E; font-weight:700; }
.sub { color:#4A6286; font-size:.95rem; margin-top:6px; }
.pill { display:inline-block; padding:4px 11px; border-radius:999px; font-size:.78rem; margin-left:6px;
        border:1px solid rgba(11,61,145,.35); color:#0B3D91; background:rgba(11,61,145,.07); }
.pill.warn { border-color: rgba(217,130,0,.55); color:#8a5400; background:rgba(217,130,0,.10); }

.kpi { --c:#14935F; background:#ffffff; border:1px solid #d5deec; border-left:5px solid var(--c); border-radius:12px;
       padding:12px 18px; margin-bottom:12px; box-shadow:0 2px 10px rgba(11,61,145,.07); }
.kpi.watch { --c:#D98200; } .kpi.bad { --c:#E03A1E; }
.kpi .l { font-size:.85rem; color:#4A6286; }
.kpi .v { font-family:'Chakra Petch',sans-serif; font-size:2.3rem; font-weight:700; color:#0B1F3A; line-height:1.15; }
.kpi .v small { font-size:1rem; color:#4A6286; font-weight:400; margin-left:4px; }
.kpi .d { font-size:.88rem; color:var(--c); font-weight:500; }

.alerta { --c:#E03A1E; background:#fff5f2; border:1px solid rgba(224,58,30,.35); border-left:5px solid var(--c);
          border-radius:12px; padding:14px 18px; margin-bottom:12px; }
.alerta h4 { margin:0 0 6px; font-family:'Chakra Petch',sans-serif; color:#8f1f0c; font-size:1.1rem; }
.alerta ul { margin:0; padding-left:18px; color:#25344f; font-size:.93rem; line-height:1.6; }
.ok { border:1px solid rgba(20,147,95,.4); background:#effaf5; color:#0d6b45; border-radius:12px; padding:14px 18px; }
.sim { border:1px solid rgba(217,130,0,.55); background:#fff8ea; color:#7a4a00; border-radius:12px;
       padding:12px 18px; margin-bottom:14px; font-family:'Chakra Petch',sans-serif; }
.nota { color:#5A6F8F; font-size:.85rem; }
h1, h2, h3 { font-family:'Chakra Petch',sans-serif !important; color:#0B3D91 !important; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color:#0B1F3A; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------ datos
@st.cache_data
def cargar_sinteticos():
    ruta = DATA_DIR / "synthetic_14_days.csv"
    if not ruta.exists():
        generar().to_csv(ruta, index=False)
    return an.cargar(ruta)


def cargar_sensor(archivo=None):
    if archivo is not None:
        return an.cargar(archivo)
    for ruta in (DATA_DIR / "sensor_log.csv",):
        if ruta.exists():
            return an.cargar(ruta)
    return None


def hr_sensor(sensor):
    if sensor is None:
        return pd.DataFrame()
    return sensor[(sensor.quality_flag == "ok") & (sensor.variable == "frecuencia_cardiaca")]


# ------------------------------------------------------------------ componentes visuales
def encabezado():
    st.markdown(
        '<div class="hdr"><div><div class="brand">LIFE<b>CORE</b></div>'
        '<div class="sub">Gemelo digital de salud</div></div></div>',
        unsafe_allow_html=True)


def kpi(etiqueta, valor, unidad, z, detalle):
    az = abs(z)
    clase = "bad" if az >= an.UMBRAL_Z else ("watch" if az >= 1.5 else "")
    estado = "Fuera de lo normal" if clase == "bad" else ("Vigilar" if clase == "watch" else "Normal")
    st.markdown(
        f'<div class="kpi {clase}"><div class="l">{etiqueta}</div>'
        f'<div class="v">{valor}<small>{unidad}</small></div>'
        f'<div class="d">{estado} · {detalle}</div></div>', unsafe_allow_html=True)


def mostrar_alertas(lista):
    if not lista:
        st.markdown('<div class="ok">Todo dentro de lo normal.</div>', unsafe_allow_html=True)
    for a in lista:
        mas = a["direccion"] == "por encima"
        if a["nombre"] == "Sueño":
            titulo = "Horas de sueño más altas de lo normal" if mas else "Horas de sueño más bajas de lo normal"
        else:
            titulo = f'{a["nombre"]} más {"alta" if mas else "baja"} de lo normal'
        st.markdown(
            f'<div class="alerta"><h4>{titulo}</h4><ul>'
            f'<li><b>Ahora:</b> {a["valor_ultimo"]:.1f} {a["unidad"]} (lo normal: {a["mediana_base"]:.1f} {a["unidad"]}).</li>'
            f'<li><b>Desde:</b> {a["desde"]:%d/%m/%Y}, {a["dias"]} días seguidos.</li>'
            f'<li><b>Conviene revisar:</b> sueño, actividad y carga de trabajo.</li></ul></div>', unsafe_allow_html=True)


def vigentes(lista, ultimo_dia):
    """Alertas que siguen activas en el último día (las que ya se recuperaron no cuentan)."""
    return [a for a in lista if a["hasta"] >= ultimo_dia]


def estado_receptor():
    """Estado del receptor WiFi (receptor.py). None si no está en ejecución."""
    try:
        with urllib.request.urlopen("http://localhost:8000/estado", timeout=0.8) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _panel_vivo():
    e = estado_receptor()
    b = base["frecuencia_cardiaca"]
    if e is None or e["edad_s"] is None or e["edad_s"] > 4:
        st.session_state.pop("vivo_base", None)             # sin señal: se recalibra al volver
    if e is None:
        st.warning("El receptor o el dispositivo está apagado.")
        return
    if e["edad_s"] is None or e["edad_s"] > 4:
        st.info("Esperando latidos. Coloca el dedo en el sensor.")
        return
    rec = e["recientes"] or [e["bpm"]]
    med = float(pd.Series(rec[-12:]).median())
    vb = st.session_state.get("vivo_base")
    if vb is None and len(rec) >= 20:                       # línea base propia: primeros 20 latidos válidos
        r = pd.Series(rec[-20:]); m0 = float(r.median()); mad = float((r - m0).abs().median())
        vb = st.session_state["vivo_base"] = {"med": m0, "escala": max(1.4826 * mad, 0.08 * m0)}
    if vb is None:
        kpi("Frecuencia cardiaca (en vivo)", f"{e['bpm']}", "lpm", 0.0, f"calibrando, {len(rec)}/20 latidos")
    else:
        z = (med - vb["med"]) / vb["escala"]
        kpi("Frecuencia cardiaca (en vivo)", f"{e['bpm']}", "lpm", z,
            f"promedio reciente {med:.0f} lpm · lo tuyo {vb['med']:.0f} lpm")
    st.markdown(f'<p class="nota">Latidos recibidos: {e["seq"]}</p>', unsafe_allow_html=True)


panel_vivo = st.fragment(run_every=2)(_panel_vivo) if hasattr(st, "fragment") else _panel_vivo


def columnas():
    """Holograma + panel. En modo grande el holograma ocupa todo el ancho y el panel queda debajo."""
    if st.session_state.get("holo_grande"):
        return st.container(), st.container()
    return st.columns([5, 2], gap="medium")


def alto_holo(altura=None):
    return 900 if st.session_state.get("holo_grande") else (altura or 820)


def holo(bpms, estado, sub, fuente, altura=None, live=False):
    altura = alto_holo(altura)
    b = base["frecuencia_cardiaca"]
    html = holograma_html(bpms, estado, "AST-001", sub, fuente, live=live,
                          base={"med": b["mediana"], "escala": b["escala"], "umbral": an.UMBRAL_Z})
    es_url = html.startswith("/app/static/")
    if hasattr(st, "iframe"):          # Streamlit reciente
        st.iframe(html, height=altura)
    elif es_url:                       # versiones anteriores: iframe dentro de components.html
        components.html(f'<iframe src="{html}" style="width:100%;height:{altura-6}px;border:0"></iframe>', height=altura)
    else:
        components.html(html, height=altura)
    st.caption(ATRIBUCION)


def figura(dia_df, base, var, altura=300):
    nombre, unidad = an.VARIABLES[var]
    b = base[var]
    s = an.con_z(dia_df[dia_df.variable == var], base).sort_values("dia")
    fig = go.Figure()
    fig.add_vrect(x0=b["inicio"], x1=b["fin"], fillcolor="#0B3D91", opacity=0.05, line_width=0,
                  annotation_text="línea base", annotation_position="top left",
                  annotation_font=dict(size=11, color="#5A6F8F"))
    fig.add_hrect(y0=b["mediana"] - an.UMBRAL_Z * b["escala"], y1=b["mediana"] + an.UMBRAL_Z * b["escala"],
                  fillcolor=CIAN, opacity=0.10, line_width=0)
    fig.add_hline(y=b["mediana"], line_dash="dash", line_color="rgba(11,61,145,.55)")
    fig.add_trace(go.Scatter(x=s.dia, y=s.value, mode="lines+markers", name=nombre,
                             line=dict(color=CIAN, width=2.5), marker=dict(size=6, color=CIAN)))
    fuera = s[s.z.abs() >= an.UMBRAL_Z]
    fig.add_trace(go.Scatter(x=fuera.dia, y=fuera.value, mode="markers", name="Fuera de banda",
                             marker=dict(color="rgba(224,58,30,.22)", size=15, symbol="circle",
                                         line=dict(color=ROJO, width=2))))
    estilo_ejes(fig, unidad)
    fig.update_layout(title=dict(text=f"{nombre} · mediana diaria", font=dict(size=15)), height=altura)
    return fig


def estilo_ejes(fig, unidad=""):
    fig.update_layout(
        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#25344f"), margin=dict(l=10, r=10, t=44, b=10),
        legend=dict(orientation="h", y=-0.18), yaxis_title=unidad)
    fig.update_xaxes(gridcolor="rgba(11,61,145,.10)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(11,61,145,.10)", zeroline=False)


HORIZONTE = 7

# ------------------------------------------------------------------ cálculo
df = cargar_sinteticos()
dia = an.diario(df)
base = an.linea_base(dia)
alertas = an.alertas(dia, base)
dz = an.con_z(dia, base)
ultimo = {v: dz[dz.variable == v].sort_values("dia").iloc[-1] for v in an.VARIABLES}
hr_alerta = any(a["variable"] == "frecuencia_cardiaca" for a in alertas)

encabezado()
st.sidebar.toggle("Holograma grande (ancho completo)", key="holo_grande")
pagina = st.sidebar.radio("Pantalla", ["Centro de control", "Perfil individual", "Estado actual",
                                       "Evolución temporal", "Alertas explicables",
                                       "Simulador", "Sensor en vivo (demo)"])

# ------------------------------------------------------------------ pantallas
if pagina == "Centro de control":
    sensor = cargar_sensor()
    hs = hr_sensor(sensor)
    opciones = ["Gemelo (datos sintéticos)", "Sensor en vivo (WiFi)"] + (["Sensor XD-58C (grabación)"] if len(hs) else [])
    fuente = st.radio("Fuente del latido", opciones, horizontal=True)
    dias = sorted(dia.dia.unique())
    if fuente.startswith("Gemelo"):
        k = st.select_slider("Día de misión", options=list(range(1, len(dias) + 1)), value=len(dias),
                             help="Mueve el gemelo por la misión: el cuerpo y las alertas cambian con el día.")
        corte = dias[k - 1]
        dia_k = dia[dia.dia <= corte]
        al_k = an.alertas(dia_k, base)                       # solo lo que se sabía ese día
        dz_k = an.con_z(dia_k, base)
        ult_k = {v: dz_k[dz_k.variable == v].sort_values("dia").iloc[-1] for v in an.VARIABLES}
        hr_al = any(x["variable"] == "frecuencia_cardiaca" for x in al_k)
        alerta_k = bool(vigentes(al_k, corte))
        c1, c2 = columnas()
        with c1:
            holo([ult_k["frecuencia_cardiaca"].value], "alerta" if alerta_k else "normal",
                 f"Día {k} de {len(dias)} · {fase_mision(k)}", f"{corte:%d/%m/%Y}")
        with c2:
            for var, (n, u) in an.VARIABLES.items():
                r = ult_k[var]
                kpi(n, f"{r.value:.1f}", u, r.z, f"{r.value - base[var]['mediana']:+.1f} respecto a lo normal")
            st.markdown(f'<p class="nota">Día {k} de {len(dias)} · alertas activas: {len(al_k)}</p>', unsafe_allow_html=True)
        st.markdown("### Alertas activas")
        mostrar_alertas(al_k)
    elif fuente.startswith("Sensor en vivo"):
        c1, c2 = columnas()
        with c1:
            holo([72], "normal", "Latido en tiempo real", "SENSOR EN VIVO · WiFi", live=True)
        with c2:
            panel_vivo()
    else:
        med = hs.value.median()
        zs = (med - base["frecuencia_cardiaca"]["mediana"]) / base["frecuencia_cardiaca"]["escala"]
        c1, c2 = columnas()
        with c1:
            holo(hs.value.tolist(), "alerta" if abs(zs) >= an.UMBRAL_Z else "normal",
                 "Reproducción de la grabación", "SENSOR XD-58C")
        with c2:
            kpi("Mediana del sensor", f"{med:.0f}", "lpm", zs, f"tu normal: {base['frecuencia_cardiaca']['mediana']:.0f} lpm")

elif pagina == "Perfil individual":
    st.subheader("Línea base individual")
    st.write(f"Lo normal de cada variable, calculado con los primeros {an.DIAS_BASE} días de la misión.")
    filas = []
    for var, b in base.items():
        n, u = an.VARIABLES[var]
        filas.append({"Variable": n, "Unidad": u, "Valor normal": round(b["mediana"], 1),
                      "Variación típica": round(b["escala"], 1), "Días usados": b["n_dias"]})
    st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)

elif pagina == "Estado actual":
    st.subheader("Última observación por variable")
    cols = st.columns(len(an.VARIABLES), gap="large")
    for col, (var, (n, u)) in zip(cols, an.VARIABLES.items()):
        r = ultimo[var]
        with col:
            kpi(n, f"{r.value:.1f}", u, r.z, f"{r.dia:%d/%m/%Y}")

elif pagina == "Evolución temporal":
    for var in an.VARIABLES:
        st.plotly_chart(figura(dia, base, var), use_container_width=True)
    st.markdown('<p class="nota">La franja gris marca los días de referencia; los círculos rojos, los días fuera de lo normal.</p>', unsafe_allow_html=True)

elif pagina == "Alertas explicables":
    st.subheader("Alertas")
    mostrar_alertas(alertas)
    st.markdown(f'<p class="nota">Una alerta se activa cuando algo se sale de lo normal {an.PERSISTENCIA} días seguidos; '
                'una lectura suelta no cuenta.</p>', unsafe_allow_html=True)

elif pagina == "Simulador":
    k1, k2, k3 = st.columns(3)
    var = k1.selectbox("Variable a modificar", list(an.VARIABLES), format_func=lambda v: an.VARIABLES[v][0])
    n_ult = k2.slider("Aplicar a los últimos N días", 0, 14, 4)
    u = an.VARIABLES[var][1]
    rd = an.RANGO_DELTA.get(var, 30.0)
    delta = k3.slider(f"Cambio hipotético ({u})", -rd, rd, 0.0, rd / 60)
    dias_m = sorted(dia.dia.unique())
    desde = st.slider("Proyectar desde el día de la misión", 5, len(dias_m), len(dias_m),
                      help="Mira la misión como si hoy fuera ese día y el resto no se supiera todavía.")
    st.markdown(f'<div class="ok"><b>Etapa de la misión:</b> {fase_mision(desde)} · día {desde} de {len(dias_m)} · {pd.Timestamp(dias_m[desde - 1]):%d/%m/%Y}</div>', unsafe_allow_html=True)
    dia_v = dia[dia.dia <= dias_m[desde - 1]]
    sim = an.aplicar_escenario(dia_v, var, delta, n_ult)
    al_sim = an.alertas(sim, base)
    hr_sim = an.con_z(sim, base)
    hr_ult = hr_sim[hr_sim.variable == "frecuencia_cardiaca"].sort_values("dia").iloc[-1].value
    entorno = st.radio("¿Dónde estará el astronauta los próximos días?", list(an.ENTORNOS), horizontal=True,
                       format_func=lambda e: an.ENTORNOS[e],
                       help="En órbita el pulso baja un poco. Al aterrizar sube, sobre todo de pie "
                            "(+38 % el día del aterrizaje en los astronautas del Transbordador).")
    proys = {v: an.proyectar(sim, base, v, HORIZONTE, entorno=entorno) for v in an.VARIABLES}
    s1, s2 = st.columns([2, 1])
    # Only situations that make sense where the astronaut is: no launch in orbit or on landing, nothing from the ISS on Earth
    permitidas = {"tendencia": list(an.SITUACIONES), "orbita": ["eva", "ejercicio", "sueno_iss"], "regreso": []}[entorno]
    sit = s1.selectbox("Situación de misión (datos de la NASA)", ["ninguna"] + permitidas, key=f"sit_{entorno}",
                       format_func=lambda s: "Ninguna" if s == "ninguna" else an.SITUACIONES[s]["nombre"],
                       disabled=not permitidas,
                       help="Agrega un evento real de misión al futuro. En órbita no hay despegue y en el aterrizaje "
                            "ya no hay eventos de la estación, por eso algunas opciones no aparecen.")
    dia_ev = s2.slider("Día en que ocurre", 1, HORIZONTE, 3, disabled=(sit == "ninguna"))
    if sit != "ninguna":
        S = an.SITUACIONES[sit]
        rango = (f"Pulso esperado: {S['hr_min']}–{S['hr_pico']} lpm (media {S['hr_media']}). "
                 if "hr_media" in S else f"Sueño esperado: {S['sueno']} h por noche. ")
        st.markdown(f'<div class="ok"><b>{S["nombre"]}.</b> {rango}{S["texto"]}<br>'
                    f'<small>Fuente: {S["fuente"]}</small></div>', unsafe_allow_html=True)
        proys = {v: an.aplicar_situacion(p, base, v, sit, dia_ev) for v, p in proys.items()}
    # With a scenario selected, open directly on the day that shows its effect (event day, or day 1)
    k0 = dia_ev if sit != "ninguna" else (1 if entorno != "tendencia" else 0)
    k = st.slider("Ver el estado dentro de … días", 0, HORIZONTE, k0, key=f"k_{entorno}_{sit}_{dia_ev}",
                  help="0 es el último día con datos; los demás son proyección. Mueve el slider para ver el holograma de cada día futuro.")
    c1, c2 = columnas()
    with c1:
        fig = figura(sim, base, var, 340)
        p = proys[var]
        if p is not None:
            pr = p["proy"]
            fig.add_trace(go.Scatter(x=list(pr.dia) + list(pr.dia[::-1]), y=list(pr.hi) + list(pr.lo[::-1]),
                                     fill="toself", fillcolor="rgba(31,111,209,.12)", line=dict(width=0),
                                     name="Rango esperado", hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=pr.dia, y=pr.value, mode="lines+markers", name="Proyección",
                                     line=dict(color=AZUL_CL, width=2.5, dash="dot"),
                                     marker=dict(size=6, symbol="circle-open")))
            if k:
                fig.add_vline(x=pr.dia.iloc[k - 1], line_dash="dot", line_color="rgba(11,61,145,.5)")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("### Qué podría pasar")
        hay = False
        activas = {a["variable"] for a in al_sim}
        for v, p in proys.items():
            if p is None or p["alerta"] is None:
                continue
            hay = True
            al, fin = p["alerta"], p["proy"].iloc[-1]
            nombre, uni = an.VARIABLES[v]
            cond = ("Si sigue la tendencia de los últimos días"
                    if entorno == "tendencia" or v != "frecuencia_cardiaca"
                    else ("Con el pulso de un astronauta en órbita" if entorno == "orbita"
                          else "Con el regreso a la gravedad"))
            if v in activas:
                titulo = f"{nombre}: seguiría fuera de lo normal"
                linea = f"{cond}, llegaría a {fin.value:.1f} {uni} en {HORIZONTE} días."
            else:
                titulo = f"{nombre}: saldría de lo normal el {al.dia:%d/%m} (en {int(al.k)} días)"
                linea = f"{cond}, llegaría a {al.value:.1f} {uni}."
            st.markdown(
                f'<div class="alerta"><h4>{titulo}</h4><ul><li>{linea}</li>'
                f'<li>{an.MALESTARES_ENTORNO.get((v, entorno)) or an.MALESTARES[(v, bool(al.z > 0))]}</li></ul></div>',
                unsafe_allow_html=True)
        if not hay:
            st.markdown('<div class="ok">Con este escenario no se esperan alertas en los próximos '
                        f'{HORIZONTE} días.</div>', unsafe_allow_html=True)
        st.markdown("### Alertas con los datos actuales")
        mostrar_alertas(al_sim)
    with c2:
        ph = proys["frecuencia_cardiaca"]
        if k and ph is not None:
            fila = ph["proy"].iloc[k - 1]
            hr_v, z_v = float(fila.value), float(fila.z)
            alerta_h = abs(z_v) >= an.UMBRAL_Z
            sub = f"Proyección · {fila.dia:%d/%m} (+{k})"
        else:
            hr_v = hr_ult
            alerta_h = bool(vigentes([a for a in al_sim if a["variable"] == "frecuencia_cardiaca"], sim.dia.max()))
            sub = "Último día con datos"
        holo([hr_v], "alerta" if alerta_h else "normal", sub, "SIMULADOR", altura=800)

else:
    st.subheader("Sensor en vivo")
    modo = st.radio("Modo", ["En vivo (WiFi)", "Grabación"], horizontal=True)
    if modo.startswith("En vivo"):
        v1, v2 = columnas()
        with v1:
            holo([72], "normal", "Latido en tiempo real", "SENSOR EN VIVO · WiFi", altura=820, live=True)
        with v2:
            panel_vivo()
        st.stop()
    subido = st.file_uploader("¿Otro CSV de observaciones? (opcional)", type="csv")
    sensor = cargar_sensor(subido)
    ok = hr_sensor(sensor)
    if sensor is None or not len(ok):
        st.info("No hay lecturas válidas. Inicia receiver/receiver.py con el ESP32 encendido o sube un CSV.")
    else:
        b = base["frecuencia_cardiaca"]
        med = ok.value.median()
        z = (med - b["mediana"]) / b["escala"]
        c1, c2 = columnas()
        with c1:
            holo(ok.value.tolist(), "alerta" if abs(z) >= an.UMBRAL_Z else "normal",
                 "Reproducción de la grabación", "SENSOR XD-58C", altura=680)
        with c2:
            kpi("Mediana del sensor", f"{med:.0f}", "lpm", z, f"tu normal: {b['mediana']:.0f} lpm")
            st.markdown(f'<p class="nota">Lecturas: {len(sensor)} · válidas: {len(ok)}</p>', unsafe_allow_html=True)
        fig = go.Figure(go.Scatter(x=ok.timestamp, y=ok.value, mode="lines+markers", name="lpm",
                                   line=dict(color=CIAN, width=2), marker=dict(size=4)))
        fig.add_hrect(y0=b["mediana"] - an.UMBRAL_Z * b["escala"], y1=b["mediana"] + an.UMBRAL_Z * b["escala"],
                      fillcolor=CIAN, opacity=0.10, line_width=0)
        estilo_ejes(fig, "lpm")
        fig.update_layout(height=280, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
