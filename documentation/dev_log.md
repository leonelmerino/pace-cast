# pace-cast — bitacora tecnica de implementacion

Este documento registra, en orden cronologico, las decisiones tomadas durante la implementacion de `pace-cast`, los problemas encontrados (muchos de ellos de entorno/hardware, no de codigo) y como se resolvieron. El objetivo es que quien retome el proyecto entienda el *por que* detras de decisiones que no son obvias mirando solo el codigo final.

Incluye citas textuales de los pedidos del usuario donde aportan contexto.

## 1. Scaffold inicial

El proyecto nace de un resumen pasado desde otra conversacion (el usuario ya habia definido el stack en un chat previo con Claude, sin acceso a esta sesion de Claude Code):

> Quiero construir una prueba de concepto en Windows que use un HTC VIVE Ultimate Tracker como sensor de movimiento para controlar la reproduccion de un video [...] Stack propuesto: Python + pyopenvr para pose, scipy.signal.find_peaks para cadencia, servidor WebSocket, app con `<video>` HTML5 ajustando `playbackRate` con `preservesPitch = true`.

Se implemento tal cual estaba especificado:

- `python/pose_reader.py`: lee la pose del primer `TrackedDeviceClass_GenericTracker` visible en SteamVR via `IVRSystem.getDeviceToAbsoluteTrackingPose`, a ~90 Hz. Incluye modo `--simulate` (caminata sintetica sinusoidal, sin depender de OpenVR) pensado para poder desarrollar/probar el resto del pipeline sin hardware conectado.
- `python/cadence.py`: remuestrea la posicion vertical del tracker a una grilla uniforme (30 Hz) y usa `scipy.signal.find_peaks` sobre una ventana deslizante de 4 s para estimar pasos/min. Mapea cadencia -> `playbackRate` linealmente (100 pasos/min = 1.0x, clamp `[0.25x, 2.0x]`).
- `python/server.py`: pega ambas piezas y expone un servidor WebSocket (`ws://localhost:8765`) que transmite `{cadence, playbackRate}` a ~15 Hz a todos los clientes conectados.
- `app/index.html` + `app/app.js` + `app/style.css`: pagina simple con `<video>`, que se conecta al WebSocket y ajusta `video.playbackRate` (con `preservesPitch = true` para no distorsionar el tono del audio). Se descarto Electron a favor de una pagina estatica: para un POC no aportaba nada que un navegador normal no resolviera, y evitaba la complejidad de empaquetado/build de Electron.

## 2. Nombre y creacion del repo

Se pidieron 5 ideas de nombre para el repositorio de GitHub; el usuario eligio **pace-cast**.

## 3. Identidad de git no configurada

Al intentar el primer commit local:

```
fatal: unable to auto-detect email address
```

Git no tenia `user.name`/`user.email` configurados en esta maquina. Las reglas de la sesion prohiben tocar la configuracion de git sin permiso explicito del usuario (ni siquiera `--global`), asi que se le pregunto directamente. Se configuro **solo a nivel de este repo** (sin `--global`) con:


Aclaracion importante que surgio en la conversacion: el **username de GitHub** y el **`user.name`/`user.email` de git** (autor del commit, texto libre) son cosas distintas — el username de GitHub se usa recien al armar la URL del remoto (`github.com/<usuario>/pace-cast`), no en `git config`.

## 4. Sin GitHub CLI (`gh`)

`gh` no estaba instalado, asi que no se pudo automatizar la creacion del repo remoto. Se dejo el commit local y se le paso al usuario el flujo manual (crear repo vacio en github.com, `git remote add origin ...`, `git push -u origin master`). El usuario lo resolvio por su cuenta — se detecto porque un `git status` posterior ya mostraba `Your branch is up to date with 'origin/master'` con el remoto ya configurado.

## 5. Fuente de video: local vs. URL vs. archive.org

Primer intento: dejar el video en el propio repo. Se le explico al usuario el limite duro de GitHub (**100 MB por archivo** via git normal, warning a partir de 50 MB) y que superarlo requiere Git LFS.

El usuario prefirio usar un video de **archive.org** en streaming directo, sin commitear nada pesado al repo. Se valido el approach antes de implementarlo:

```bash
curl -sI "https://archive.org/download/wpmma-Walking_the_Cross_Town_Trail/Walking_the_Cross_Town_Trail.mp4"
```

confirmando `Accept-Ranges: bytes` (necesario para que el `<video>` pueda hacer seek sin descargar todo el archivo) y `Access-Control-Allow-Origin: *` (sin problemas de CORS al cargarlo desde un origen distinto). Se agrego un formulario de URL a la app (`app/index.html` + `app/app.js`).

## 6. Tercera fuente: lista de videos predefinidos

Pedido explicito del usuario:

> debieramos tener estas opciones, reproducir un video local, poner una URL de un video, o cargar un video de una lista. El primer video de la lista sera este https://archive.org/details/wpmma-Walking_the_Cross_Town_Trail

Se creo `app/videos.js` con un array `VIDEO_LIBRARY` (`{label, url}`), que `app.js` usa para poblar dinamicamente el `<select id="list-select">`. Agregar un video nuevo a la lista es editar ese archivo, nada mas.

## 7. Friccion para probar la app en un navegador

Varios obstaculos de entorno antes de poder ver la app funcionando, ninguno relacionado al codigo en si:

1. **El navegador sandbox de esta sesion (Claude Browser) renderiza `file://` fuera de la carpeta de proyecto original como "static snapshot"** (sin ejecutar JS). Abrir `app/index.html` directamente con `file://` no serviria para probar nada interactivo desde esa herramienta.
2. **`preview_start` (para levantar servidores accesibles en `http://localhost`) exige el archivo `.claude/launch.json` en la carpeta que quedo fijada como "proyecto" al iniciar la sesion** (`xr-collaboration-proto2`, un repo distinto y no relacionado), no en la carpeta de trabajo actual (`pace-cast`) aunque el `cwd` del shell se haya cambiado explicitamente. Esto genero confusion inicial (se intento crear/editar cosas en la carpeta equivocada); una vez identificado, se opto por **no** tocar el otro repo y en su lugar levantar el servidor manualmente y pedirle al usuario que lo abriera en su propio navegador.
3. **Ni Python ni Node estaban instalados** en la maquina (solo el alias-stub de Microsoft Store para `python`, que solo abre la Store). Con permiso explicito del usuario se instalo Python 3.11.9 via:
   ```bash
   winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
   ```
   y luego se creo el venv e instalaron las dependencias (`openvr`, `numpy`, `scipy`, `websockets`).

Solucion final para probar: servir `app/` con `python -m http.server 5500 --directory app` y pedirle al usuario que abriera `http://localhost:5500` **en su propio navegador** (el navegador sandbox de la sesion bloquea `http://localhost` directo por politica salvo a traves de `preview_start`, que aqui no aplicaba por el punto 2).

## 8. Validacion end-to-end en modo `--simulate`

Antes de tener SteamVR/hardware listos, se valido el pipeline completo (WebSocket -> deteccion de cadencia -> `playbackRate` -> UI) corriendo `python server.py --simulate` (marcha sintetica ~96 pasos/min, sin tocar OpenVR). El usuario confirmo que la cadencia y la velocidad se movian solas en la interfaz.

Bug menor encontrado en el camino: al correr el servidor en segundo plano con su stdout redirigido a un archivo (no a una terminal interactiva), Python usa *block buffering* y el mensaje de arranque no aparecia en el log hasta llenar el buffer. Solucion: correr con `python -u` (modo unbuffered) para depuracion.

## 9. Overlay de cadencia/velocidad en pantalla completa

Pedido:

> quisiera ver si podemos agregar informacion superpuesta al video cuando esta a pantalla completa.. seria bueno poder ver la velocidad y cadencia

Problema tecnico conocido de antemano: el boton **nativo** de fullscreen de un `<video>` fullscreenea unicamente ese elemento — cualquier overlay hermano en el DOM quedaria fuera de la vista en pantalla completa.

Solucion: envolver `<video>` en `#video-wrapper` (`position: relative`), poner el HUD (`#hud`) como `position: absolute` **dentro** de ese wrapper, y usar un boton propio que llama a `videoWrapper.requestFullscreen()` (fullscreenea el wrapper completo, overlay incluido) en vez de depender del boton nativo del video. Para evitar que alguien use el nativo por error (rompiendo el overlay), se agrego `controlsList="nofullscreen"` al `<video>`.

## 10. Bug: el boton de fullscreen se veia "deshabilitado"

Dos sintomas reportados por el usuario en momentos distintos, con la misma raiz (controles de formulario sin estilo propio):

1. El **icono nativo** de fullscreen del reproductor se veia visible pero atenuado/translucido, en vez de desaparecer. Causa: en algunas versiones de Chromium, `controlsList="nofullscreen"` deja el boton nativo *visible-pero-deshabilitado* en lugar de removerlo del todo.
   - Fix: `video::-webkit-media-controls-fullscreen-button { display: none !important; }` para forzar que desaparezca por completo.
2. El **boton propio** ("Pantalla completa", agregado en la fila de controles) tambien parecia deshabilitado. Causa mas probable: `:root { color-scheme: light dark; }` hace que los controles de formulario sin estilo explicito adopten la apariencia nativa oscura del SO/navegador, que a simple vista se confunde con un estado deshabilitado.
   - Fix: estilo explicito para todos los `<button>` (fondo azul solido `#2563eb`, texto blanco, estados hover/active), quitando la ambiguedad visual.

Ademas se agrego manejo de errores al pedir fullscreen (`.catch` + `alert` con el mensaje de error), para que una falla real del navegador (en vez de un malentendido de estilos) sea visible de inmediato en vez de fallar en silencio.

## 11. SteamVR: `InitError_Init_HmdNotFound`

Al intentar correr `server.py` **sin** `--simulate` (tracker real, ya emparejado y con SteamVR abierto), fallo con:

```
openvr.error_code.InitError_Init_HmdNotFound
```

Causa: `openvr.init(openvr.VRApplication_Other)` (usado en `pose_reader.py`) igual requiere que SteamVR detecte un headset (HMD) real para inicializar por completo — un setup de "solo trackers, sin headset" no arranca por defecto.

Diagnostico confirmado leyendo:

```
C:\Program Files (x86)\Steam\steamapps\common\SteamVR\drivers\null\resources\settings\default.vrsettings
```

que tenia `"enable": false` en la seccion `driver_null`. Ese driver "null" es un headset falso que SteamVR trae para exactamente este caso (setups de tracking sin HMD, comunes en full-body-tracking).

**Esta accion la ejecuto el usuario, no el asistente** (por decision explicita del usuario, tratandose de un archivo de configuracion de una aplicacion externa al repo, fuera del alcance de "cambios de proyecto"): cambiar `"enable"` a `true`, cerrar SteamVR por completo y reabrirlo.

Pregunta de seguimiento del usuario: si esto rompe el uso normal de SteamVR con un headset real en otro proyecto suyo. Respuesta razonada (no verificada empiricamente en su hardware): `driver_null` declara `"loadPriority": -999`, muy por debajo de los drivers de headsets reales (que no fijan prioridad explicita), por lo que SteamVR deberia preferir automaticamente un HMD real cuando este conectado — no deberia hacer falta alternar el flag entre proyectos, pero se le recomendo verificarlo una vez conectando el headset real con el driver null ya habilitado.

## 12. Primera prueba real exitosa

Con el driver null habilitado y el tracker en estado "Ready" (buena iluminacion, dongle en puerto sin interferencia), `server.py` (sin `--simulate`) conecto sin errores. El usuario confirmo:

> funciona casi perfecto, el movimiento de mis pasos acelera el video y la cadencia y velocidad se actualizan.

## 13. Warning del navegador: `--enable-unsafe-webgpu`

El usuario vio un banner de Chrome/Edge advirtiendo sobre el flag de linea de comandos `--enable-unsafe-webgpu`. Se verifico (`grep` sobre todo el repo) que no hay ninguna referencia a WebGPU en el codigo de `pace-cast` — el flag no puede ser activado por una pagina web, viene de como se lanzo esa instancia del navegador (acceso directo modificado, otra herramienta, etc.), y es irrelevante para esta app ya que no usa WebGPU en absoluto.

## 14. Ajustes finales de overlay y descubribilidad del boton de fullscreen

Ultimo pedido de ajuste visual:

> en la implementacion actual el overlay esta en la esquina superior me gustaria que estuviera mas en el centro de la imagen hacia abajo y que usemos un color que lo destaque mas, quizas azul.

y, tras una vuelta adicional (moverlo a la fila de controles hizo que quedara "perdido" entre otros elementos):

> con el ultimo cambio el icono de full screen ya no aparece (ni siquiera deshabilitado) y no puedo poner el video en full screen

(la confusion era que el usuario buscaba el icono nativo, ya ocultado a proposito, y no habia notado el boton propio en la fila de controles).

Cambios finales:

- **HUD**: reposicionado a `left: 50%; bottom: 14%; transform: translateX(-50%)` (centrado horizontal, hacia la parte baja del video), color `#4da3ff` (azul), `font-weight: 700`, tamano de fuente mayor y `text-shadow` para legibilidad sobre cualquier contenido de video.
- **Boton de fullscreen**: movido de la fila de controles genericos a un overlay propio dentro de `#video-wrapper`, posicionado en la esquina superior derecha **del video mismo** (como en reproductores estandar tipo YouTube), con icono `⛶` + texto, para que sea inmediatamente visible junto al video en vez de competir visualmente con el selector de video/formulario de URL.

## Problemas conocidos / pendientes

- La deteccion de cadencia (`find_peaks` sobre la posicion vertical) no distingue una marcha intencional de otros movimientos del tracker (ajustarselo, quitarselo, dejarlo en el suelo) — puede generar falsos picos y cadencias espurias.
- `baseline_cadence = 100` (pasos/min = 1.0x) es un valor arbitrario de partida, no calibrado contra la velocidad de camara real de ningun video especifico. Ver seccion "Pendiente" del README.
- No hay suavizado (ej. EMA o filtro pasa-bajos) sobre `playbackRate` antes de enviarlo por WebSocket; cambios bruscos de cadencia se reflejan de inmediato y podrian sentirse abruptos durante la reproduccion.
- `TrackerPoseReader._find_tracker` retorna el primer `GenericTracker` que encuentra en SteamVR; con mas de un tracker emparejado simultaneamente el comportamiento no esta definido (tomaria uno cualquiera).
- El comportamiento del driver "null" de SteamVR conviviendo con un headset real (seccion 11) no fue verificado empiricamente, solo razonado a partir de `loadPriority`.

## Referencia rapida de archivos

| Archivo | Rol |
|---|---|
| `python/pose_reader.py` | Lectura de pose via OpenVR (o marcha sintetica en `--simulate`) |
| `python/cadence.py` | Deteccion de picos / cadencia (pasos/min) y mapeo a `playbackRate` |
| `python/server.py` | Servidor WebSocket que conecta pose + cadencia y transmite a los clientes |
| `app/index.html` | Estructura de la UI: video, HUD, controles de fuente de video |
| `app/app.js` | Logica de cliente: WebSocket, carga de video (archivo/URL/lista), fullscreen |
| `app/style.css` | Estilos, incluyendo el overlay HUD y el fix de icono nativo de fullscreen |
| `app/videos.js` | Lista editable de videos de ejemplo para el selector |
