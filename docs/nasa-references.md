# Reference values and sources

Lifecore is **calibrated** with published values; its data remain synthetic. Group averages are not individual limits.

## Resting heart rate on Earth
- Normal adult resting range: **60-100 bpm**. Below 60 (non-athletes) or above 100 deserves attention.
  Sources: Mayo Clinic, *What's a normal resting heart rate?*; AARP citing the American Heart Association.
  Used for: gray below 60, blue normal range, yellow when approaching 100.

## Spaceflight and return to gravity (NASA)
Source: NASA NTRS 20040201532, *Section 1 Cardiovascular Deconditioning* (Space Shuttle, 4-5 day flights).

| Moment | Supine | Standing |
|---|---|---|
| Preflight (n = 32) | 57 bpm | 75 bpm |
| Landing day | 70 bpm (+18 %) | 101 bpm (+38 %) |
| 7-10 days after | 57 bpm | 78 bpm |

- Presyncopal astronauts on landing day: **72 bpm supine, 114 bpm standing**. Non-presyncopal: 62 and 91 bpm (n = 29).
- Highest value recorded after touchdown: **160 bpm** (n = 34).
- Stroke volume index falls about 17 % on landing day; cardiac output is maintained by a higher heart rate.

**Used for:** red zone starting at **114 bpm** (standing heart rate of astronauts close to fainting); the gravity scenario *landing* (+38 % on day 1, back to baseline in about 8 days, "7 to 10 days" in the source).

## In orbit
- NASA, *Evidence Report: Risk of Cardiac Rhythm Problems During Spaceflight* (NTRS 20170005625): in-flight heart rate and blood pressure were lower than preflight; long-duration crews had relative bradycardia (no absolute values given).
- ISS long-duration flights, 8 astronauts (PMC6789148, leg cuff test): resting heart rate before the cuff release was **56 +/- 6 bpm in flight versus 57 +/- 6 supine on Earth** before the flight. Supine 57 -> 65 bpm postflight.
- In microgravity there is no supine/standing difference.

**Used for:** the gravity scenario *in orbit*.

## Exercise
- ISS exercise sessions peak at about 162-163 bpm; prescriptions target 70-90 % of maximum heart rate (NASA/SP-2025-0273).

## Our own assumptions (not from the sources)
- In orbit the daily average is **3 bpm lower** than a normal Earth day (because there is no upright posture).
- Recovery after landing takes **8 days** in the model.
- Yellow starts at about 80-90 bpm, so the color warns before 100 bpm.
- Sleep and activity effects in the synthetic mission are invented to show the alert logic.

## Links
- https://www.mayoclinic.org/healthy-lifestyle/fitness/expert-answers/heart-rate/faq-20057979
- https://www.aarp.org/health/healthy-living/what-is-a-healthy-heart-rate/
- https://ntrs.nasa.gov/api/citations/20040201532/downloads/20040201532.pdf
- https://ntrs.nasa.gov/api/citations/20170005625/downloads/20170005625.pdf
- https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6789148/
- https://www.nasa.gov/wp-content/uploads/2025/02/sp-20250000273.pdf

## Mission situations in the Simulator

The Simulator can inject a NASA-documented event into the 7-day forecast (`analysis.SITUACIONES`):

| Situation | Values used | Source |
|---|---|---|
| Launch | 88–110 bpm (Apollo 11 crew peaks) | Apollo 11 Mission Report, Biomedical Evaluation |
| Spacewalk (EVA) | 88–160 bpm; ≥140 sustained triggered a crew advisory in Gemini XII | NASA NTRS 20120003917 |
| ISS exercise | peak 162–163 bpm; 70–90 % of max HR prescribed (mean 145 is an assumption) | NASA/SP-2025-0273 |
| Sleep like the ISS | 6.1 h per night vs 8.5 h scheduled | Barger et al., Lancet Neurology 2014 |

## SpO₂ and temperature

| Variable | Why NASA cares | Normal reference used | Future sensor |
|---|---|---|---|
| SpO₂ | Hypoxia risk (cabin atmosphere, EVA suit) | Healthy 95–100 %; personal baseline ≈ 97.5 %; minimum "normal variation" 0.8 % | Pulse oximeter (e.g. MAX30102) |
| Temperature | Thermal regulation and physiological context | Baseline ≈ 36.6 °C; minimum "normal variation" 0.2 °C | Thermal sensor |

Both are synthetic for now (4 readings/day) and stay inside normal limits in the default 14-day data; use the Simulator to see what a drop in SpO₂ or a fever would trigger.
