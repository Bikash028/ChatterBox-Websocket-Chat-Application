from fastapi import FastAPI, WebSocket
import uvicorn

# Initilize
app = FastAPI()

# Simple GET API to test server
# check route
@app.get("/")
async def home():
    return {
        "message": "WebSocket Server is Running"
        }

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(socket: WebSocket):
    # Accept the connection
    await socket.accept()
    print("Client connected")

    try:
        while True:
            # Receive message from client
            message = await socket.receive_text()
            print(f"Received from client: {message}")

            # Send response back to client
            await socket.send_text(f"Server received: {message}")

    except Exception as e:
        print("client disconnected",e)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000,reload=True) 

