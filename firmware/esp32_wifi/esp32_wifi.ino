#include <WiFi.h>
#include <HTTPClient.h>

#include "secrets.h"

const int PIN_SENSOR = 34;
const int LED = 2;

const unsigned long TS_US = 10000;
const float AMP_BANDA_MIN = 60;
const unsigned long REFRACTARIO = 300;
const unsigned long SIN_LATIDO_MAX = 3000;

struct Biquad {
  float b0, b1, b2, a1, a2, x1, x2, y1, y2;
  float paso(float x) {
    float y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
    x2 = x1; x1 = x; y2 = y1; y1 = y;
    return y;
  }
};
Biquad pasaAltos = {0.956543226f, -1.913086451f, 0.956543226f, -1.911197067f, 0.914975835f, 0, 0, 0, 0};
Biquad pasaBajos = {0.046131802f, 0.092263604f, 0.046131802f, -1.307285029f, 0.491812237f, 0, 0, 0, 0};

const int N_INT = 8;
unsigned long intervalos[N_INT]; int nInt = 0, idxInt = 0;
float alturas[N_INT]; int nAlt = 0, idxAlt = 0;
float umbral = 0, sPrev = 0, sPrev2 = 0, sMax = -1e9, sMin = 1e9, ampBanda = 0;
bool hayDedo = false, bloqueado = false;
int muestrasVentana = 0, muestrasTotal = 0;
unsigned long ultimoLatido = 0, ultimoWifi = 0, tSiguiente = 0;
float bpmSuave = 0;

unsigned long medianaIntervalos() {
  unsigned long t[N_INT]; for (int i = 0; i < nInt; i++) t[i] = intervalos[i];
  for (int i = 1; i < nInt; i++) { unsigned long k = t[i]; int j = i - 1; while (j >= 0 && t[j] > k) { t[j + 1] = t[j]; j--; } t[j + 1] = k; }
  return t[nInt / 2];
}
float medianaAlturas() {
  float t[N_INT]; for (int i = 0; i < nAlt; i++) t[i] = alturas[i];
  for (int i = 1; i < nAlt; i++) { float k = t[i]; int j = i - 1; while (j >= 0 && t[j] > k) { t[j + 1] = t[j]; j--; } t[j + 1] = k; }
  return t[nAlt / 2];
}

bool ritmoRegular() {
  if (nInt < 6) return false;
  unsigned long med = medianaIntervalos();
  for (int i = 0; i < nInt; i++) if (intervalos[i] < 0.7 * med || intervalos[i] > 1.3 * med) return false;
  return true;
}
void olvidarRitmo() { nInt = 0; idxInt = 0; nAlt = 0; idxAlt = 0; ultimoLatido = 0; bloqueado = false; }

void conectar() {
  if (WiFi.status() == WL_CONNECTED) return;
  if (millis() - ultimoWifi < 5000) return;
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
  tSiguiente = micros();
  Serial.println("Iniciando...");
}

void candidatoLatido(unsigned long t) {
  unsigned long dt = t - ultimoLatido;
  if (ultimoLatido != 0 && dt < REFRACTARIO) return;
  bool primero = (ultimoLatido == 0);
  if (!primero && nInt >= 3) {
    unsigned long med = medianaIntervalos();
    if (dt < 0.6 * med) return;
    if (dt > 1.6 * med) {
      ultimoLatido = t; return;
    }
  }
  if (!primero && dt < 2000) {
    intervalos[idxInt] = dt; idxInt = (idxInt + 1) % N_INT; if (nInt < N_INT) nInt++;
  } else if (!primero) {
    nInt = 0; idxInt = 0; bloqueado = false;
  }
  ultimoLatido = t;
  digitalWrite(LED, HIGH);
  if (!bloqueado && ritmoRegular()) bloqueado = true;
  if (bloqueado && nInt >= 3) {
    bpmSuave = 60000.0 / medianaIntervalos();
    Serial.printf("LATIDO,%d,%s\n", (int)bpmSuave, WiFi.status() == WL_CONNECTED ? "wifi" : "sinwifi");
    enviar((int)bpmSuave);
  }
  digitalWrite(LED, LOW);
}

void loop() {
  conectar();
  unsigned long ahoraUs = micros();
  if ((long)(ahoraUs - tSiguiente) < 0) return;
  tSiguiente += TS_US;
  if ((long)(ahoraUs - tSiguiente) > 5 * (long)TS_US) tSiguiente = ahoraUs + TS_US;

  int crudo = 0; for (int i = 0; i < 4; i++) crudo += analogRead(PIN_SENSOR);
  float s = pasaBajos.paso(pasaAltos.paso(crudo / 4.0f));
  unsigned long ms = millis();
  if (++muestrasTotal < 200) { sPrev2 = sPrev; sPrev = s; return; }

  if (s > sMax) sMax = s;
  if (s < sMin) sMin = s;
  if (++muestrasVentana >= 150) {
    ampBanda = sMax - sMin;
    hayDedo = ampBanda >= AMP_BANDA_MIN;
    if (hayDedo && nAlt == 0) umbral = 0.5f * sMax;
    if (!hayDedo) olvidarRitmo();
    Serial.printf("AMP,%d,%s\n", (int)ampBanda, hayDedo ? "dedo" : "sin dedo");
    sMax = -1e9; sMin = 1e9; muestrasVentana = 0;
  }

  if (hayDedo) {

    if (sPrev > sPrev2 && sPrev >= s && sPrev > umbral && umbral > 0) {
      unsigned long antes = ultimoLatido;
      candidatoLatido(ms - 10);
      if (ultimoLatido != antes) {
        alturas[idxAlt] = sPrev; idxAlt = (idxAlt + 1) % N_INT; if (nAlt < N_INT) nAlt++;
        umbral = 0.5f * medianaAlturas();
      }
    }
    if (ultimoLatido != 0 && ms - ultimoLatido > SIN_LATIDO_MAX) olvidarRitmo();
  }
  sPrev2 = sPrev; sPrev = s;
}
