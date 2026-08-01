"""Deteccion de cadencia (pasos/min) a partir de la posicion vertical del
tracker, y mapeo de cadencia a velocidad de reproduccion de video."""
from collections import deque

import numpy as np
from scipy.signal import find_peaks


class CadenceDetector:
    def __init__(self, window_seconds: float = 4.0, sample_rate_hint: int = 90):
        self.window_seconds = window_seconds
        maxlen = int(window_seconds * sample_rate_hint * 1.5)
        self._times = deque(maxlen=maxlen)
        self._values = deque(maxlen=maxlen)

    def add_sample(self, timestamp: float, y: float):
        self._times.append(timestamp)
        self._values.append(y)

    def cadence_steps_per_min(self) -> float:
        if len(self._times) < 8:
            return 0.0

        times = np.array(self._times)
        values = np.array(self._values)

        cutoff = times[-1] - self.window_seconds
        mask = times >= cutoff
        times, values = times[mask], values[mask]
        if len(times) < 8:
            return 0.0

        # Remuestrea a una grilla uniforme para que "distance" en find_peaks
        # (en muestras) corresponda a una distancia real de tiempo.
        fs = 30.0
        grid = np.arange(times[0], times[-1], 1.0 / fs)
        if len(grid) < 8:
            return 0.0
        resampled = np.interp(grid, times, values)
        resampled = resampled - resampled.mean()

        min_step_seconds = 0.25  # limite superior: 240 pasos/min
        peaks, _ = find_peaks(resampled, distance=int(fs * min_step_seconds), prominence=0.01)
        if len(peaks) < 2:
            return 0.0

        intervals = np.diff(grid[peaks])
        avg_interval = np.mean(intervals)
        if avg_interval <= 0:
            return 0.0

        return 60.0 / avg_interval


def cadence_to_playback_rate(
    cadence: float,
    baseline_cadence: float = 100.0,
    min_rate: float = 0.25,
    max_rate: float = 2.0,
) -> float:
    """Mapeo lineal: caminar a baseline_cadence pasos/min equivale a 1.0x.

    cadence <= 0 (sin marcha detectada) devuelve 0.0, que la app interpreta
    como "pausar el video".
    """
    if cadence <= 0:
        return 0.0
    rate = cadence / baseline_cadence
    return float(np.clip(rate, min_rate, max_rate))
