import asyncio
from fastapi import APIRouter, WebSocket
from chat_service import streaming

router = APIRouter()

async def main(websocket):
    task = asyncio.create_task(streaming(websocket))
    await asyncio.gather(task)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await main(websocket)
    except Exception as e:
        print(f"WebSocket Endpoint Error: {e}")
        await websocket.close()

@router.get("/test")
async def test():
    print("/test called.")
