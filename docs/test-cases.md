# Test cases and results

Results below were obtained on **2026-11-14** (Python 3.13, Streamlit 1.67, headless Chromium for the hologram).

## A. Automated tests - `python tests/test_analysis.py`

| ID | What is tested | Expected | Result |
|---|---|---|---|
| TC01 | Baseline length and value | 7 days; median heart rate 63-69 bpm | PASS |
| TC02 | Low-quality sample (injected 140 bpm) | Flagged `baja`, does not move the daily median | PASS |
| TC03 | One isolated spike (90 bpm on one day) | No alert (needs 2 consecutive days) | PASS |
| TC04 | Three consecutive high days | One alert, direction "above", 3 days | PASS |
| TC05 | Three consecutive low days | One alert, direction "below" | PASS |
| TC06 | Synthetic mission | Alerts for heart rate and sleep only (no false alerts on activity) | PASS |
| TC07 | Hologram colors | Mission has a gray day (< 60), blue, yellow, orange and a red day (>= 114) | PASS |
| TC08 | Forecast | 7 days, band wider than the line on both sides | PASS |
| TC09 | Forecast limits | Sleep forecast never below 0 h | PASS |
| TC10 | Gravity scenarios | Orbit = baseline - 3 bpm; landing day 1 = baseline x 1.38; landing recovers afterwards | PASS |
| TC11 | CSV vs generator | Saved CSV has the same rows and variables as the generator | PASS |

Output: `11/11 passed`.

## B. Application tests (Streamlit AppTest, no exceptions)

| ID | Scenario | Result |
|---|---|---|
| TC20 | App starts | PASS |
| TC21 | Open each page: profile, current state, trends, alerts, simulator, live sensor | PASS (6/6, no exception) |
| TC22 | Simulator: "start forecast from day 10", all three gravity environments | PASS; day 10 + landing forecasts 91.8 bpm on the next day |
| TC23 | Simulator with what-if slider (-23.5 bpm on the last day) | PASS; hologram turns blue when the last day is back in range |

## C. Hologram visual checks (headless Chromium + screenshots, see `docs/images/`)

| ID | Scenario | Expected | Result |
|---|---|---|---|
| TC30 | Day 3, 57 bpm | Gray, label "BAJO" | PASS |
| TC31 | Day 10, 84 bpm | Yellow, label "SUBIENDO" | PASS |
| TC32 | Day 14, 122 bpm | Red, label "MUY ALTO" | PASS |
| TC33 | Click on the heart | Camera zooms to the heart, "Volver" button appears | PASS |
| TC34 | Live mode, no signal | Shows "--" and a flat ECG, no invented beats | PASS |
| TC35 | Live mode with simulated receiver (71 -> 113 bpm) | Color changes with the pulse | PASS |

## D. Hardware tests (ESP32 + XD-58C)

| ID | Scenario | Result |
|---|---|---|
| TC40 | ESP32 joins the PC hotspot and posts beats | PASS (serial monitor shows `LATIDO,<bpm>,wifi`) |
| TC41 | Stable reading with a finger on the sensor | PASS (reported by the team) |
| TC42 | False beats with no finger on the sensor | Firmware finger gate (`AMP_MIN`), 450 ms refractory period and regularity check added; **pending re-confirmation on the device** |
| TC43 | Sensor over clothing | Not tested; the optical sensor needs skin contact |

## Known limitations found while testing
- A single day outside the normal range is shown red in the KPI card but does not create an alert (by design, 2 days are required).
- The orbit effect (-3 bpm) is an assumption; see [nasa-references.md](nasa-references.md).
