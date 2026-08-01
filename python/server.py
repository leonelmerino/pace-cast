"""Puente WebSocket: lee la pose del tracker via SteamVR, calcula la cadencia
de marcha y transmite {cadence, playbackRate} a los clientes conectados."""
import argparse
import asyncio
import json
import time

import websockets

from cadence import CadenceDetector, cadence_to_playback_rate
from pose_reader import TrackerPoseReader

POLL_HZ = 90
BROADCAST_HZ = 15


async def broadcaster(reader: TrackerPoseReader, clients: set):
    detector = CadenceDetector()
    poll_interval = 1.0 / POLL_HZ
    broadcast_interval = 1.0 / BROADCAST_HZ
    last_broadcast = 0.0

    while True:
        pose = reader.read()
        if pose.valid:
            detector.add_sample(pose.timestamp, pose.y)

        now = time.time()
        if now - last_broadcast >= broadcast_interval:
            last_broadcast = now
            cadence = detector.cadence_steps_per_min()
            playback_rate = cadence_to_playback_rate(cadence)
            payload = json.dumps(
                {"cadence": round(cadence, 1), "playbackRate": round(playback_rate, 3)}
            )
            if clients:
                await asyncio.gather(*(c.send(payload) for c in clients), return_exceptions=True)

        await asyncio.sleep(poll_interval)


async def handle_client(websocket, clients: set):
    clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        clients.discard(websocket)


async def main():
    parser = argparse.ArgumentParser(description="pace-cast: tracker -> websocket bridge")
    parser.add_argument("--simulate", action="store_true", help="usa un caminante sintetico en vez de SteamVR")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    reader = TrackerPoseReader(simulate=args.simulate)
    reader.connect()
    print(f"Tracker listo (simulate={reader.simulate}). Sirviendo en ws://{args.host}:{args.port}")

    clients = set()
    try:
        async with websockets.serve(lambda ws: handle_client(ws, clients), args.host, args.port):
            await broadcaster(reader, clients)
    finally:
        reader.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
