// Lifecore - ESP32 + XD-58C pulse sensor (signal on GPIO34) -> WiFi -> PC (receiver/receiver.py)
// Beat detection without external libraries: adaptive threshold, 450 ms refractory period, median of the last
// 8 intervals, outlier rejection and a finger-presence gate. Demonstration prototype, not a medical device.
#include <WiFi.h>
#include <HTTPClient.h>

// WiFi settings live in secrets.h (copy secrets.h.example to secrets.h and edit it; secrets.h is git-ignored)
#include "secrets.h"

const int PIN_SENSOR = 34;
const int LED = 2;

int umbral = 2048, picoMax = 0, valleMin = 4095;
const int AMP_MIN = 200;           // amplitud mínima de la señal para considerar que hay un dedo (ajusta con las líneas AMP)
int ampActual = 0;                 // amplitud de la última ventana de 1.5 s
unsigned long ultimoLatido = 0, ultimaAdaptacion = 0, ultimoWifi = 0;
bool sobre = false;
float bpmSuave = 0;
const int N_INT = 8;                 // intervalos recientes para la mediana
unsigned long intervalos[N_INT]; int nInt = 0, idxInt = 0, rechazos = 0;

unsigned long medianaIntervalos();
// ritmo regular: pide >= 6 intervalos y que todos estén dentro de ±25 % de la mediana (el ruido no es regular)
bool ritmoRegular() {
  if (nInt < 6) return false;
  unsigned long med = medianaIntervalos();
  for (int i = 0; i < nInt; i++) if (intervalos[i] < 0.75 * med || intervalos[i] > 1.25 * med) return false;
  return true;
}

unsigned long medianaIntervalos() {
  unsigned long t[N_INT]; for (int i = 0; i < nInt; i++) t[i] = intervalos[i];
  for (int i = 1; i < nInt; i++) { unsigned long k = t[i]; int j = i - 1; while (j >= 0 && t[j] > k) { t[j + 1] = t[j]; j--; } t[j + 1] = k; }
  return t[nInt / 2];
}

void conectar() {
  if (WiFi.status() == WL_CONNECTED) return;
  if (millis() - ultimoWifi < 5000) return;      // reintenta cada 5 s sin bloquear la medición
  ultimoWifi = millis();
  WiFi.disconnect(); WiFi.begin(WIFI_SSID, WIFI_PASS);
}

void enviar(int bpm) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.setTimeout(800);
  http.begin(URL_PC);
  http.addHeader("Content-Type", "application/json");
  http.POST("{\"bpm\":" + String(bpm) + "}");
  http.end();
}

void setup() {
  Serial.begin(115200);
  pinMode(LED, OUTPUT);
  analogReadResolution(12);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.println("Iniciando...");
}

void loop() {
  conectar();
  int v = analogRead(PIN_SENSOR);
  unsigned long ahora = millis();

  if (v > picoMax) picoMax = v;
  if (v < valleMin) valleMin = v;
  if (ahora - ultimaAdaptacion > 1500) {          // el umbral sigue la amplitud de la señal
    ampActual = picoMax - valleMin;
    if (ampActual >= AMP_MIN) umbral = (picoMax + valleMin) / 2;
    else { nInt = 0; idxInt = 0; rechazos = 0; ultimoLatido = 0; }   // sin dedo: descarta lo acumulado
    Serial.printf("AMP,%d,%s\n", ampActual, ampActual >= AMP_MIN ? "dedo" : "sin dedo");
    picoMax = v; valleMin = v; ultimaAdaptacion = ahora;
  }

  if (ampActual < AMP_MIN) { sobre = false; delay(5); return; }   // sin señal de pulso: no detecta latidos

  if (!sobre && v > umbral + 40) {                // flanco de subida = candidato a latido
    unsigned long dt = ahora - ultimoLatido;
    if (ultimoLatido != 0 && dt < 450) {          // periodo refractario: ignora la muesca dicrota / rebotes
      sobre = true;
    } else {
      sobre = true;
      if (ultimoLatido == 0 || dt > 1800) {       // primer latido o pausa larga: reinicia
        nInt = 0; idxInt = 0; rechazos = 0; ultimoLatido = ahora;
      } else {
        bool aceptar = true;
        if (nInt >= 3) {                          // rechaza intervalos muy distintos a la mediana reciente
          unsigned long med = medianaIntervalos();
          if (dt < 0.65 * med || dt > 1.5 * med) aceptar = false;
        }
        if (aceptar) {
          rechazos = 0;
          intervalos[idxInt] = dt; idxInt = (idxInt + 1) % N_INT; if (nInt < N_INT) nInt++;
          ultimoLatido = ahora;
          if (nInt >= 3) {                        // envía solo cuando ya hay base para estimar
            bpmSuave = 60000.0 / medianaIntervalos();
            digitalWrite(LED, HIGH);
            Serial.printf("LATIDO,%d,%s\n", (int)bpmSuave, WiFi.status() == WL_CONNECTED ? "wifi" : "sinwifi");
            enviar((int)bpmSuave);
            digitalWrite(LED, LOW);
          }
        } else if (++rechazos >= 4) {             // si se rechaza varias veces seguidas, el ritmo cambió: reinicia
          nInt = 0; idxInt = 0; rechazos = 0; ultimoLatido = ahora;
        }
      }
    }
  }
  if (sobre && v < umbral - 40) sobre = false;
  delay(5);
}
