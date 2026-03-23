from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
from datetime import datetime

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# -----------------------------
# Chat Manager
# -----------------------------
class ChatManager:
    def __init__(self):
        self.connections = []
        self.user_map = {}
        self.room_map = {}
        self.chat_history = {}

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        username = self.user_map.get(ws, "Someone")
        room = self.room_map.get(ws)

        if ws in self.connections:
            self.connections.remove(ws)

        self.user_map.pop(ws, None)
        self.room_map.pop(ws, None)

        return username, room

    async def broadcast(self, room: str, data: dict):
        dead = []
        for conn in self.connections:
            if self.room_map.get(conn) == room:
                try:
                    await conn.send_json(data)
                except:
                    dead.append(conn)

        for d in dead:
            self.disconnect(d)


manager = ChatManager()

# -----------------------------
# ROUTE (HTML FILE)
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# -----------------------------
# WEBSOCKET
# -----------------------------
@app.websocket("/ws")
async def websocket(ws: WebSocket):

    await manager.connect(ws)

    username = None
    room = None

    try:
        while True:
            data = await ws.receive_json()
            event = data.get("type")

            if event == "join":

                if username is None:
                    username = data.get("username")
                    manager.user_map[ws] = username

                old_room = manager.room_map.get(ws)
                new_room = data.get("room")

                manager.room_map[ws] = new_room

                if old_room:
                    await manager.broadcast(old_room, {
                        "type": "system",
                        "message": f"{username} left {old_room}"
                    })

                await manager.broadcast(new_room, {
                    "type": "system",
                    "message": f"{username} joined {new_room} 👋"
                })

                # send history
                history = manager.chat_history.get(new_room, [])
                for msg in history:
                    await ws.send_json(msg)

                room = new_room

            elif event == "chat":
                time = datetime.now().strftime("%H:%M")

                msg_data = {
                    "type": "chat",
                    "username": username,
                    "message": data.get("message"),
                    "time": time
                }

                if room not in manager.chat_history:
                    manager.chat_history[room] = []

                manager.chat_history[room].append(msg_data)

                await manager.broadcast(room, msg_data)

            elif event == "typing":
                await manager.broadcast(room, {
                    "type": "typing",
                    "username": username
                })

            elif event == "stop_typing":
                await manager.broadcast(room, {
                    "type": "stop_typing"
                })

    except WebSocketDisconnect:
        user, room = manager.disconnect(ws)

        await manager.broadcast(room, {
            "type": "system",
            "message": f"{user} left {room} ❌"
        })


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)