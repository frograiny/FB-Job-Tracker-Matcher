import asyncio
import json
import os
import websockets

async def main():
    ws_url = os.environ.get("AGY_BROWSER_WS_URL")
    if not ws_url:
        print("AGY_BROWSER_WS_URL not set in env.")
        return
    print(f"Connecting to: {ws_url}")
    try:
        async with websockets.connect(ws_url) as websocket:
            # Get targets
            message = {
                "id": 1,
                "method": "Target.getTargets"
            }
            await websocket.send(json.dumps(message))
            response = await websocket.recv()
            data = json.loads(response)
            print("Targets:")
            for target in data.get("result", {}).get("targetInfos", []):
                print(f"- Type: {target.get('type')}, URL: {target.get('url')}, ID: {target.get('targetId')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
