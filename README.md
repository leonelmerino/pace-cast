# pace-cast

POC: usar un HTC VIVE Ultimate Tracker como sensor de marcha para controlar la velocidad de reproduccion de un video pregrabado (walkthrough en primera persona). Al "marchar" en el lugar, la cadencia detectada ajusta `video.playbackRate` en tiempo real, manteniendo el tono del audio (`preservesPitch`).

## Hardware

- HTC VIVE Ultimate Tracker + VIVE Wireless Dongle (USB-C), conectado a un PC Windows.
- SteamVR corriendo en background (obligatorio: es el unico camino para leer la pose del tracker via OpenVR).

Nota: este pipeline solo funciona en Windows. SteamVR no tiene soporte funcional en macOS.

## Estructura

```
pace-cast/
  python/     # lectura de pose (OpenVR), deteccion de cadencia, servidor WebSocket
  app/        # interfaz web: <video> controlado por playbackRate
```

## Setup

### 1. Python (lectura de tracker + servidor)

```bash
cd python
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Con SteamVR abierto y el tracker emparejado:

```bash
python server.py
```

Sin hardware, para probar el pipeline con un caminante sintetico:

```bash
python server.py --simulate
```

Esto levanta un servidor WebSocket en `ws://localhost:8765`.

### 2. App web

Abre `app/index.html` en el navegador (Chrome/Edge), elige un archivo de video local y comienza a marchar. La cadencia detectada (pasos/min) se traduce a `playbackRate`; sin movimiento el video se pausa.

## Como funciona

1. `python/pose_reader.py` consulta la pose del tracker generico via `IVRSystem.GetDeviceToAbsoluteTrackingPose` a ~90 Hz.
2. `python/cadence.py` remuestrea la posicion vertical, detecta picos (`scipy.signal.find_peaks`) y calcula pasos/min sobre una ventana deslizante de 4 s.
3. `python/server.py` mapea cadencia -> `playbackRate` (lineal, 100 pasos/min = 1.0x, rango [0.25x, 2.0x]) y lo transmite por WebSocket a ~15 Hz.
4. `app/app.js` recibe el mensaje y ajusta `video.playbackRate`, manteniendo `preservesPitch = true` para evitar distorsion de tono en el audio.

## Pendiente

- Calibrar `baseline_cadence` y el rango de `playbackRate` contra la velocidad real de camara del video (metros/paso del walkthrough).
- Filtrar falsos positivos de `find_peaks` cuando el tracker se mueve por otras razones (ajustarselo, quitarselo, etc).
- Suavizado adicional de `playbackRate` (ej. EMA) si los cambios de velocidad se sienten bruscos.
