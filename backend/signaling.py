from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict
import json
import uuid
import asyncio

app = FastAPI()

rooms: Dict[str, Dict] = {}
connections: Dict[str, WebSocket] = {}


async def keep_alive(ws: WebSocket):
    while True:
        await asyncio.sleep(25)
        await ws.send_text(json.dumps({"type": "ping"}))


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    asyncio.create_task(keep_alive(ws))

    client_id = str(uuid.uuid4())
    role = None
    room_id = None
    connections[client_id] = ws

    try:
        while True:
            data = json.loads(await ws.receive_text())
            msg_type = data.get("type")

            if msg_type == "join":
                role = data["role"]
                room_id = data["roomId"]

                if room_id not in rooms:
                    rooms[room_id] = {"sender": None, "listeners": {}}

                if role == "sender":
                    rooms[room_id]["sender"] = client_id
                    print("Sender joined:", room_id)

                elif role == "listener":
                    rooms[room_id]["listeners"][client_id] = ws
                    sender_id = rooms[room_id]["sender"]

                    if sender_id:
                        await connections[sender_id].send_text(json.dumps({
                            "type": "listener_joined",
                            "listenerId": client_id
                        }))

            elif msg_type == "offer":
                listener_id = data["listenerId"]
                await connections[listener_id].send_text(json.dumps({
                    "type": "offer",
                    "offer": data["offer"],
                    "listenerId": listener_id
                }))

            elif msg_type == "answer":
                sender_id = rooms[room_id]["sender"]
                await connections[sender_id].send_text(json.dumps({
                    "type": "answer",
                    "answer": data["answer"],
                    "listenerId": data["listenerId"]
                }))

            elif msg_type == "candidate":
                listener_id = data.get("listenerId")
                target_id = listener_id or rooms[room_id]["sender"]

                if target_id in connections:
                    await connections[target_id].send_text(json.dumps({
                        "type": "candidate",
                        "candidate": data["candidate"],
                        "listenerId": listener_id
                    }))

            elif msg_type == "broadcast_end":
                room = rooms.pop(room_id, None)
                if room:
                    for ws in room["listeners"].values():
                        await ws.send_text(json.dumps({"type": "broadcast_end"}))

    except WebSocketDisconnect:
        pass

    finally:
        connections.pop(client_id, None)
        if room_id in rooms:
            if role == "listener":
                rooms[room_id]["listeners"].pop(client_id, None)
                sender_id = rooms[room_id]["sender"]
                if sender_id:
                    await connections[sender_id].send_text(json.dumps({
                        "type": "listener_left",
                        "listenerId": client_id
                    }))
            if role == "sender":
                for ws in rooms[room_id]["listeners"].values():
                    await ws.send_text(json.dumps({"type": "broadcast_end"}))
                rooms.pop(room_id, None)
