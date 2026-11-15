"""Automated test cases for the analysis module and the synthetic data.

Run from the repository root:  python tests/test_analysis.py   (or: pytest tests)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import analysis as an                      # noqa: E402
import synthetic_data as sd                # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data" / "synthetic_14_days.csv"


def _daily(df):
    return an.diario(df)


def _series(values, variable="frecuencia_cardiaca", start="2026-10-30"):
    days = pd.date_range(start, periods=len(values))
    return pd.DataFrame({"variable": variable, "dia": days, "value": values})


def test_tc01_baseline_uses_first_7_days():
    d = _daily(sd.generar())
    base = an.linea_base(d)
    assert base["frecuencia_cardiaca"]["n_dias"] == 7
    assert 63 <= base["frecuencia_cardiaca"]["mediana"] <= 69


def test_tc02_low_quality_samples_are_ignored():
    df = sd.generar()
    assert (df.quality_flag == "baja").sum() == 1            # the injected 140 bpm outlier
    day5 = _daily(df).query("variable=='frecuencia_cardiaca'").iloc[4].value
    assert day5 < 80                                          # the outlier did not move the daily median


def test_tc03_single_day_outlier_does_not_raise_alert():
    values = [66, 65, 67, 66, 65, 66, 67, 90, 66, 65]          # one isolated spike on day 8
    d = _series(values)
    assert an.alertas(d, an.linea_base(d)) == []


def test_tc04_two_consecutive_days_raise_alert():
    values = [66, 65, 67, 66, 65, 66, 67, 95, 96, 97]
    d = _series(values)
    al = an.alertas(d, an.linea_base(d))
    assert len(al) == 1 and al[0]["direccion"] == "por encima" and al[0]["dias"] == 3


def test_tc05_alert_direction_below():
    values = [66, 65, 67, 66, 65, 66, 67, 50, 49, 48]
    d = _series(values)
    al = an.alertas(d, an.linea_base(d))
    assert len(al) == 1 and al[0]["direccion"] == "por debajo"


def test_tc06_mission_data_alerts():
    d = _daily(sd.generar())
    al = an.alertas(d, an.linea_base(d))
    assert {a["variable"] for a in al} == {"frecuencia_cardiaca", "sueno_horas"}


def test_tc07_color_days_cover_gray_to_red():
    hr = _daily(sd.generar()).query("variable=='frecuencia_cardiaca'").value.tolist()
    assert min(hr) < 60                                       # gray day
    assert any(60 <= v < 80 for v in hr)                      # blue
    assert any(88 <= v < 100 for v in hr)                     # yellow
    assert any(100 <= v < 114 for v in hr)                    # orange
    assert max(hr) >= 114                                     # red


def test_tc08_forecast_has_7_days_and_band():
    d = _daily(sd.generar())
    p = an.proyectar(d, an.linea_base(d), "frecuencia_cardiaca", 7)
    assert len(p["proy"]) == 7
    assert (p["proy"].hi > p["proy"].value).all() and (p["proy"].lo < p["proy"].value).all()


def test_tc09_forecast_is_damped_and_bounded():
    d = _daily(sd.generar())
    p = an.proyectar(d, an.linea_base(d), "sueno_horas", 7)
    assert p["proy"].value.min() >= 0                         # sleep cannot go below 0 h


def test_tc10_gravity_environments():
    d = _daily(sd.generar()).query("dia <= '2026-11-05'")
    base = an.linea_base(d)
    orbit = an.proyectar(d, base, "frecuencia_cardiaca", 7, entorno="orbita")["proy"].value
    landing = an.proyectar(d, base, "frecuencia_cardiaca", 7, entorno="regreso")["proy"].value
    med = base["frecuencia_cardiaca"]["mediana"]
    assert abs(orbit.iloc[0] - (med - 3)) < 1e-6              # orbit: 3 bpm lower
    assert abs(landing.iloc[0] - med * 1.38) < 1e-6           # landing: +38 % on the first day
    assert landing.iloc[-1] < landing.iloc[0]                 # recovers over the following days


def test_tc11_csv_matches_generator():
    assert DATA.exists()
    saved = pd.read_csv(DATA)
    fresh = sd.generar()
    assert len(saved) == len(fresh)
    assert set(saved.variable) == {"frecuencia_cardiaca", "sueno_horas", "actividad_min", "spo2", "temperatura_c"}


def test_spo2_temperature():
    d = an.diario(sd.generar()); b = an.linea_base(d)
    assert 96 <= b["spo2"]["mediana"] <= 99 and 36 <= b["temperatura_c"]["mediana"] <= 37.2
    assert all(v["escala"] > 0 for v in b.values())
    low = an.aplicar_escenario(d, "spo2", -6.0, 4)       # hypothetical hypoxia
    assert any(a["variable"] == "spo2" for a in an.alertas(low, b))
    hot = an.aplicar_escenario(d, "temperatura_c", 1.5, 4)  # hypothetical fever
    assert any(a["variable"] == "temperatura_c" for a in an.alertas(hot, b))
    assert an.proyectar(d, b, "spo2", 7)["proy"].value.max() <= 100


def test_nasa_situations():
    d = an.diario(an.cargar(str(DATA))) if "DATA" in globals() else an.diario(sd.generar())
    b = an.linea_base(d)
    r = an.proyectar(d, b, "frecuencia_cardiaca", 7)
    x = an.aplicar_situacion(r, b, "frecuencia_cardiaca", "ejercicio", 3)
    assert x["proy"].value.iloc[2] == an.SITUACIONES["ejercicio"]["hr_media"]
    r = an.proyectar(d, b, "sueno_horas", 7)
    x = an.aplicar_situacion(r, b, "sueno_horas", "sueno_iss", 2)
    assert (x["proy"].value.iloc[1:] == 6.1).all()


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn(); print(f"PASS  {name}")
        except AssertionError as e:
            failed += 1; print(f"FAIL  {name}  {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
