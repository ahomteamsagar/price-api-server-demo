import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"symbol": "btc"}))
        while True:
            response = await websocket.recv()
            print("Received:", response)

if __name__ == "__main__":
    asyncio.run(test_websocket())
 