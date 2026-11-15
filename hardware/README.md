# Hardware

Prototype of a wearable pulse sensor that feeds the digital twin over WiFi.

## Parts
| Part | Notes |
|---|---|
| ESP32 development board (ESP32 Dev Module) | Reads the sensor and sends beats over WiFi |
| XD-58C optical pulse sensor | Analog output; needs skin contact (bare finger) |
| Jumper wires, USB cable | Power and programming |
| 3D-printed enclosure | Files in [`stl/`](stl/) |

## Wiring
| XD-58C | ESP32 |
|---|---|
| VCC (+) | 3V3 |
| GND (-) | GND |
| Signal (S) | GPIO34 (ADC1, input only) |

The sketch is in [`../firmware/esp32_wifi/`](../firmware/esp32_wifi/). Copy `secrets.h.example` to `secrets.h` first.

## 3D-printed enclosure
| File | What it is |
|---|---|
| [`stl/ORION BASE.STL`](stl/ORION%20BASE.STL) | Enclosure base (printable) |
| [`stl/ORION TAPADERA.STL`](stl/ORION%20TAPADERA.STL) | Enclosure lid (printable) |
| [`cad/ORION BASE.SLDPRT`](cad/), [`cad/ORION TAPADERA.SLDPRT`](cad/) | SolidWorks parts (editable source) |
| [`cad/los orions.SLDASM`](cad/) | SolidWorks assembly of base + lid |

Still to add next to these files: printer and material used, layer height, infill, supports, and a photo of the assembled prototype in `docs/images/`.

## Safety
This is a demonstration device. It is **not a medical device** and must not be used to diagnose or monitor health conditions.
