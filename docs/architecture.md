# Architecture

Lifecore has four layers: **sensing**, **transport**, **analysis** and **presentation**. Each can be run and tested on its own.

## Data flow

```mermaid
flowchart LR
    S[XD-58C pulse sensor] -->|analog signal, GPIO34| E[ESP32<br/>beat detection]
    E -->|HTTP POST /latido {bpm}<br/>over the PC hotspot| R[receiver/receiver.py<br/>port 8000]
    R -->|appends| L[(data/sensor_log.csv)]
    R -->|GET /estado every 200 ms| H[3D hologram<br/>Three.js]
    G[synthetic_data.py] --> D[(data/synthetic_14_days.csv)]
    D --> A[analysis.py<br/>baseline - alerts - forecast]
    L --> A
    A --> U[app/app.py<br/>Streamlit pages]
    U -->|iframe with configuration| H
```

## 1. Sensing: sensor and ESP32 (`firmware/esp32_wifi`)
- The XD-58C is an optical pulse sensor; its analog output goes to ESP32 pin GPIO34 (12-bit ADC).
- Beat detection, with no external libraries:
  - adaptive threshold = midpoint between the last peak and valley (updated every 1.5 s);
  - **finger gate:** if the signal amplitude is below `AMP_MIN` (200 ADC counts) no beats are detected;
  - 450 ms refractory period to ignore the dicrotic notch;
  - heart rate = 60000 / **median** of the last 8 beat intervals;
  - intervals outside 0.65x-1.5x of the median are rejected, and 4 rejections in a row restart the estimate.
- Each accepted beat is sent as `POST /latido {"bpm": 72}`. WiFi credentials live in `secrets.h` (git-ignored).

## 2. Transport: receiver (`receiver/receiver.py`)
- Python standard library only (`ThreadingHTTPServer`, port 8000, CORS open so the hologram can poll it).
- `POST /latido` validates the value (20-250 bpm), flags quality (`ok` / `baja` for values outside 45-160 or jumps over 25 bpm) and appends a row to `data/sensor_log.csv`.
- `GET /estado` returns `{seq, bpm, calidad, edad_s, recientes}`. `seq` increases with every beat, so the hologram makes the heart beat once per received beat. `edad_s` is the age of the last beat; older than 4 s means "no signal".

## 3. Analysis (`app/analysis.py`, pure functions)
- **Daily series:** median per day of valid (`quality_flag == ok`) observations.
- **Baseline** (first 7 days): median and MAD; robust scale = max(1.4826 x MAD, 3 % of the median).
- **z-score:** (value - baseline median) / robust scale.
- **Alert:** |z| >= 2.5 for >= 2 consecutive days in the same direction. The output includes value, normal value, start date and length, so every alert is explainable.
- **Forecast** (`proyectar`): Theil-Sen slope over the last 7 days, damped by 0.85 per day, clamped to physiological limits, with a prediction band (1.96 sigma). It reports the first day where the forecast meets the alert rule.
- **Gravity environments:** `orbita` = baseline - 3 bpm; `regreso` = baseline x (1 + 0.38 x recovery factor) where the factor falls linearly to 0 over 8 days. See [nasa-references.md](nasa-references.md).

## 4. Presentation
- **Streamlit app** (`app/app.py`): pages for the control center (hologram + KPI cards + mission-day slider), profile, current state, trends, explainable alerts, simulator (what-if sliders, forecast, gravity scenarios) and live sensor. The live panel refreshes with `st.fragment(run_every=2)`.
- **Hologram** (`hologram/src/entry.js`, bundled to `app/static/hologram/holo.js`): served by Streamlit as a static file and embedded in an iframe. The configuration (heart rates, labels, live URL) travels in the query string.
  - Models: `body.bin` (skin, skeleton, airways, vessels, organs, brain; ~17 MB) and `heart.glb`.
  - The heart is deformed in the vertex shader with a ventricular/atrial contraction envelope timed to the heart rate.
  - Click-to-focus uses a ray cast on the heart; the color blends between zones computed from the displayed bpm.

## Design decisions
- **Personal baselines over fixed thresholds**: one astronaut's normal is not another's.
- **Robust statistics (median/MAD)** so one noisy day cannot move the baseline or trigger an alert.
- **Persistence rule (2 days)** to avoid alert fatigue from isolated readings.
- **Explainability first**: every alert shows numbers a person can check by hand.
- **Standard library receiver** so the demo has no extra dependencies and runs on any PC.
