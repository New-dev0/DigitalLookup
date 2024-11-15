from fastapi import FastAPI, WebSocket
from fastapi.websockets import WebSocketDisconnect
from . import processUserRequest
from urllib.parse import unquote
from fastapi.responses import FileResponse
import json

app = FastAPI()


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/file/{file_path}")
async def read_file(file_path: str):
    return FileResponse(unquote(file_path))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received data: {data}")  # Print the received data
            message = json.loads(data)

            if message["action"] == "process_request":
                await processUserRequest(message, websocket)
            else:
                await websocket.send_text(
                    json.dumps({"status": "error", "message": "Invalid action"})
                )
    except WebSocketDisconnect:
        print("WebSocket disconnected")
