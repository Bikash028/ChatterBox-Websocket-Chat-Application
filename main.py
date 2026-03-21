from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

# -----------------------------
# Connection Manager (Clean Design)
# -----------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections = []
        self.usernames = {}
        self.rooms = {}

    async def connect(self, ws: WebSocket, username: str, room: str):
        # ❌ DO NOT call accept here
        self.active_connections.append(ws)
        self.usernames[ws] = username
        self.rooms[ws] = room

    def disconnect(self, ws: WebSocket):
        username = self.usernames.get(ws, "Someone")
        room = self.rooms.get(ws)

        if ws in self.active_connections:
            self.active_connections.remove(ws)

        self.usernames.pop(ws, None)
        self.rooms.pop(ws, None)

        return username, room

    async def broadcast(self, room: str, data: dict):
        dead_connections = []

        for connection in self.active_connections:
            if self.rooms.get(connection) == room:
                try:
                    await connection.send_json(data)
                except:
                    dead_connections.append(connection)

        # remove broken connections
        for dc in dead_connections:
            self.disconnect(dc)


manager = ConnectionManager()

# -----------------------------
# HTML FRONTEND
# -----------------------------
html = """
<!DOCTYPE html>
<html>
<head>
<title>Chatterbox </title>
<style>
body { font-family: Arial; margin:20px; }
#chat { border:1px solid #ccc; height:300px; overflow-y:auto; padding:10px; margin-bottom:10px;}
.system { color:gray; font-style:italic; }
#typing { color:green; font-size:14px;}
</style>
</head>

<body>

<h2>Real Time Chat</h2>

<label>Select Room:</label>
<select id="room">
<option value="general">General</option>
<option value="tech">Tech</option>
<option value="fun">Fun</option>
</select>

<div id="chat"></div>
<div id="typing"></div>

<input id="msg" placeholder="Type message">
<button onclick="sendMessage()">Send</button>

<script>

const chat = document.getElementById("chat");
const typingDiv = document.getElementById("typing");
const roomSelect = document.getElementById("room");

let username = prompt("Enter your name:");

const socket = new WebSocket("ws://localhost:8000/ws");

socket.onopen = () => {
    socket.send(JSON.stringify({
        type:"join",
        username:username,
        room:roomSelect.value
    }));
};

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const div = document.createElement("div");

    if(data.type === "chat"){
        div.innerHTML = "<b>"+data.username+":</b> "+data.message;
    }

    if(data.type === "system"){
        div.classList.add("system");
        div.innerText = data.message;
    }

    if(data.type === "typing"){
        typingDiv.innerText = data.username + " is typing...";
    }

    if(data.type === "stop_typing"){
        typingDiv.innerText = "";
    }

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
};

function sendMessage(){

    const msg = document.getElementById("msg").value;

    if(msg === "") return;

    socket.send(JSON.stringify({
        type:"chat",
        message:msg
    }));

    socket.send(JSON.stringify({
        type:"stop_typing"
    }));

    document.getElementById("msg").value = "";
}

document.getElementById("msg").addEventListener("input", ()=>{
    socket.send(JSON.stringify({type:"typing"}));
});

</script>

</body>
</html>
"""

# -----------------------------
# ROUTE
# -----------------------------
@app.get("/")
async def home():
    return HTMLResponse(html)

# -----------------------------
# WEBSOCKET ENDPOINT
# -----------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()   

    try:
        # First message (join)
        data = await ws.receive_json()

        username = data.get("username", "Anonymous")
        room = data.get("room", "general")

        await manager.connect(ws, username, room)

        # Join message
        await manager.broadcast(room, {
            "type": "system",
            "message": f"{username} joined {room} 👋"
        })

        # Continuous listening
        while True:
            data = await ws.receive_json()

            event = data.get("type")

            if event == "chat":
                await manager.broadcast(room, {
                    "type": "chat",
                    "username": username,
                    "message": data.get("message")
                })

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
# RUN SERVER
# -----------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)

