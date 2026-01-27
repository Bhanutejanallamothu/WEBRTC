import os
import json
from aiohttp import web

rooms = {}

async def health(request):
    return web.Response(text="ok")

async def ws_handler(request):
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)

    room_id = None
    role = None
    peer_id = id(ws)

    async for msg in ws:
        if msg.type != web.WSMsgType.TEXT:
            continue

        data = json.loads(msg.data)
        msg_type = data.get("type")

        if msg_type == "join":
            room_id = data["roomId"]
            role = data.get("role")

            rooms.setdefault(room_id, {
                "sender": None,
                "listeners": {}
            })

            if role == "sender":
                rooms[room_id]["sender"] = ws

            elif role == "listener":
                rooms[room_id]["listeners"][peer_id] = ws

                sender = rooms[room_id]["sender"]
                if sender:
                    await sender.send_str(json.dumps({
                        "type": "listener_joined",
                        "listenerId": peer_id
                    }))

        elif msg_type in ("offer", "answer", "candidate"):
            listener_id = data.get("listenerId")

            if role == "sender" and listener_id:
                listener = rooms[room_id]["listeners"].get(listener_id)
                if listener:
                    await listener.send_str(msg.data)

            elif role == "listener":
                sender = rooms[room_id]["sender"]
                if sender:
                    await sender.send_str(json.dumps({
                        **data,
                        "listenerId": peer_id
                    }))

    if room_id:
        if role == "sender":
            rooms[room_id]["sender"] = None
        elif role == "listener":
            rooms[room_id]["listeners"].pop(peer_id, None)

    return ws

app = web.Application()
app.router.add_get("/", health)
app.router.add_get("/ws", ws_handler)

port = int(os.environ.get("PORT", 8000))
web.run_app(app, host="0.0.0.0", port=port)
