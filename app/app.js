const video = document.getElementById("video");
const fileInput = document.getElementById("file-input");
const statusEl = document.getElementById("status");
const cadenceEl = document.getElementById("cadence");
const rateEl = document.getElementById("rate");

video.preservesPitch = true;
video.mozPreservesPitch = true; // Firefox legacy

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) return;
  video.src = URL.createObjectURL(file);
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
