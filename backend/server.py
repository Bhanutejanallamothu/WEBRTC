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

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            data = json.loads(msg.data)
            msg_type = data.get("type")

            if msg_type == "join":
                room_id = data.get("roomId")
                rooms.setdefault(room_id, set()).add(ws)

            else:
                for peer in rooms.get(room_id, []):
                    if peer is not ws:
                        await peer.send_str(msg.data)

        elif msg.type == web.WSMsgType.ERROR:
            pass

    if room_id and ws in rooms.get(room_id, []):
        rooms[room_id].remove(ws)

    return ws

app = web.Application()
app.router.add_get("/", health)
app.router.add_get("/ws", ws_handler)

port = int(os.environ.get("PORT", 8000))
web.run_app(app, host="0.0.0.0", port=port)
