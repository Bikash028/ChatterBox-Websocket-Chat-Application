from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

app = FastAPI()

active_users = {}
user_map = {}

page = """
<!DOCTYPE html>
<html>
<head>
    <title>Chat App</title>
</head>
<body>

<h3>Realtime Chat</h3>
<div id="box" style="height:250px; overflow:auto; border:1px solid black;"></div>

<input id="input" placeholder="Type message">
<button onclick="sendMsg()">Send</button>

<script>
const box = document.getElementById("box");
const username = prompt("Enter name:");

const socket = new WebSocket("ws://127.0.0.1:8000/ws");

socket.onopen = () => {
    socket.send(JSON.stringify({name: username}));
};

socket.onmessage = (e) => {
    const data = JSON.parse(e.data);
    const p = document.createElement("p");

    if(data.type === "msg"){
        p.innerHTML = "<b>" + data.name + ":</b> " + data.text;
    } else {
        p.innerHTML = "<i>" + data.text + "</i>";
    }

    box.appendChild(p);
};

function sendMsg(){
    const msg = document.getElementById("input").value;
    socket.send(JSON.stringify({text: msg}));
}
</script>

</body>
</html>
"""

@app.get("/")
async def index():
    return HTMLResponse(page)


@app.websocket("/ws")
async def ws_handler(ws: WebSocket):
    await ws.accept()

    data = await ws.receive_json()
    name = data.get("name", "Guest")

    active_users[ws] = True
    user_map[ws] = name

    await notify_all({"type": "info", "text": f"{name} joined"})

    try:
        while True:
            data = await ws.receive_json()
            text = data.get("text")

            if text:
                await notify_all({
                    "type": "msg",
                    "name": name,
                    "text": text
                })

    except:
        active_users.pop(ws, None)
        left = user_map.pop(ws, "User")

        await notify_all({"type": "info", "text": f"{left} left"})


async def notify_all(message):
    for user in active_users:
        await user.send_json(message)
