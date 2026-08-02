const video = document.getElementById("video");
const videoWrapper = document.getElementById("video-wrapper");
const fileInput = document.getElementById("file-input");
const urlForm = document.getElementById("url-form");
const urlInput = document.getElementById("url-input");
const listSelect = document.getElementById("list-select");
const fullscreenBtn = document.getElementById("fullscreen-btn");
const statusEl = document.getElementById("status");
const cadenceEl = document.getElementById("cadence");
const rateEl = document.getElementById("rate");

video.preservesPitch = true;
video.mozPreservesPitch = true; // Firefox legacy

function loadVideo(src) {
  video.src = src;
  video.play().catch(() => {});
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) return;
  loadVideo(URL.createObjectURL(file));
});

urlForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const url = urlInput.value.trim();
  if (!url) return;
  loadVideo(url);
});

for (const { label, url } of VIDEO_LIBRARY) {
  const option = document.createElement("option");
  option.value = url;
  option.textContent = label;
  listSelect.appendChild(option);
}

listSelect.addEventListener("change", () => {
  if (listSelect.value) loadVideo(listSelect.value);
});

fullscreenBtn.addEventListener("click", () => {
  if (document.fullscreenElement) {
    document.exitFullscreen();
  } else {
    videoWrapper.requestFullscreen();
  }
});

function connect() {
  const ws = new WebSocket("ws://localhost:8765");

  ws.onopen = () => {
    statusEl.textContent = "Conectado";
    statusEl.className = "status connected";
  };

  ws.onmessage = (event) => {
    const { cadence, playbackRate } = JSON.parse(event.data);
    cadenceEl.textContent = cadence.toFixed(0);

    if (playbackRate <= 0) {
      video.pause();
      rateEl.textContent = "0.00";
      return;
    }

    video.playbackRate = playbackRate;
    rateEl.textContent = playbackRate.toFixed(2);
    if (video.paused && video.src) {
      video.play().catch(() => {});
    }
  };

  ws.onclose = () => {
    statusEl.textContent = "Desconectado - reintentando...";
    statusEl.className = "status disconnected";
    setTimeout(connect, 1500);
  };

  ws.onerror = () => ws.close();
}

connect();
