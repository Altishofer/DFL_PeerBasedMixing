import asyncio
import subprocess
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/logs")


@router.websocket("/{container_name}")
async def stream_logs(websocket: WebSocket, container_name: str):
    await websocket.accept()

    process = await asyncio.create_subprocess_exec(
        'docker', 'logs', '-f', container_name,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    try:
        while True:
            line = await process.stdout.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue
            await websocket.send_text(line.decode().strip())
    except WebSocketDisconnect:
        pass
    finally:
        process.terminate()
        try:
            await process.wait()
        except:
            pass