"""Lee la pose del HTC VIVE Ultimate Tracker desde SteamVR via pyopenvr."""
import math
import time
from dataclasses import dataclass

try:
    import openvr
except ImportError:
    openvr = None


@dataclass
class TrackerPose:
    timestamp: float
    x: float
    y: float
    z: float
    qw: float
    qx: float
    qy: float
    qz: float
    valid: bool


def _matrix_to_quaternion(m):
    """Convierte la rotacion de un HmdMatrix34_t (openvr) a cuaternion (w, x, y, z)."""
    r00, r01, r02 = m[0][0], m[0][1], m[0][2]
    r10, r11, r12 = m[1][0], m[1][1], m[1][2]
    r20, r21, r22 = m[2][0], m[2][1], m[2][2]
    trace = r00 + r11 + r22
    if trace > 0:
        s = 0.5 / math.sqrt(trace + 1.0)
        qw = 0.25 / s
        qx = (r21 - r12) * s
        qy = (r02 - r20) * s
        qz = (r10 - r01) * s
    elif r00 > r11 and r00 > r22:
        s = 2.0 * math.sqrt(1.0 + r00 - r11 - r22)
        qw = (r21 - r12) / s
        qx = 0.25 * s
        qy = (r01 + r10) / s
        qz = (r02 + r20) / s
    elif r11 > r22:
        s = 2.0 * math.sqrt(1.0 + r11 - r00 - r22)
        qw = (r02 - r20) / s
        qx = (r01 + r10) / s
        qy = 0.25 * s
        qz = (r12 + r21) / s
    else:
        s = 2.0 * math.sqrt(1.0 + r22 - r00 - r11)
        qw = (r10 - r01) / s
        qx = (r02 + r20) / s
        qy = (r12 + r21) / s
        qz = 0.25 * s
    return qw, qx, qy, qz


class TrackerPoseReader:
    """Ubica el primer VIVE Tracker generico visible en SteamVR y expone su pose.

    En modo --simulate (o si pyopenvr no esta instalado) genera un caminante
    sintetico, para poder probar el resto del pipeline sin hardware.
    """

    def __init__(self, simulate: bool = False):
        self.simulate = simulate or openvr is None
        self._vr_system = None
        self._device_index = None
        self._sim_t0 = time.time()

    def connect(self):
        if self.simulate:
            return
        self._vr_system = openvr.init(openvr.VRApplication_Other)
        self._device_index = self._find_tracker()
        if self._device_index is None:
            raise RuntimeError(
                "No se encontro ningun VIVE Tracker generico en SteamVR. "
                "Verifica que el dongle este conectado y el tracker emparejado."
            )

    def _find_tracker(self):
        for i in range(openvr.k_unMaxTrackedDeviceCount):
            if self._vr_system.getTrackedDeviceClass(i) == openvr.TrackedDeviceClass_GenericTracker:
                return i
        return None

    def read(self) -> TrackerPose:
        return self._read_simulated() if self.simulate else self._read_real()

    def _read_real(self):
        poses = self._vr_system.getDeviceToAbsoluteTrackingPose(
            openvr.TrackingUniverseStanding, 0, openvr.k_unMaxTrackedDeviceCount
        )
        pose = poses[self._device_index]
        if not pose.bPoseIsValid:
            return TrackerPose(time.time(), 0, 0, 0, 1, 0, 0, 0, valid=False)
        m = pose.mDeviceToAbsoluteTracking.m
        x, y, z = m[0][3], m[1][3], m[2][3]
        qw, qx, qy, qz = _matrix_to_quaternion(m)
        return TrackerPose(time.time(), x, y, z, qw, qx, qy, qz, valid=True)

    def _read_simulated(self):
        # Marcha sintetica: ~1.6 Hz (~96 pasos/min), 8 cm de oscilacion vertical.
        t = time.time() - self._sim_t0
        step_hz = 1.6
        y = 0.08 * math.sin(2 * math.pi * step_hz * t)
        return TrackerPose(time.time(), 0.0, y, 0.0, 1.0, 0.0, 0.0, 0.0, valid=True)

    def close(self):
        if not self.simulate and openvr is not None:
            openvr.shutdown()
