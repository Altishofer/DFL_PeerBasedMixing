import asyncio
from collections import defaultdict
from typing import Set, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from collections import defaultdict

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
import asyncio

router = APIRouter(prefix="/logs")

log_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
log_tasks: Dict[str, asyncio.Task] = {}
log_buffers: Dict[str, str] = defaultdict(str)
last_log_line: Dict[str, str] = defaultdict(str)


@router.websocket("/{container_name}")
async def logs_websocket(websocket: WebSocket, container_name: str):
    await websocket.accept()
    log_connections[container_name].add(websocket)

    if container_name in log_buffers:
        await websocket.send_text(log_buffers[container_name])

    if container_name not in log_tasks:
        log_tasks[container_name] = asyncio.create_task(broadcast_logs(container_name))

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        log_connections[container_name].remove(websocket)
        if not log_connections[container_name]:
            task = log_tasks.pop(container_name, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            log_connections.pop(container_name, None)

async def broadcast_logs(container_name: str):
    process = await asyncio.create_subprocess_exec(
        'docker', 'logs', '-f', container_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT
    )

    try:
        while True:
            line = await process.stdout.readline()
            if not line:
                await asyncio.sleep(0.1)
                continue
            message = line.decode(errors="ignore").strip()

            if message == last_log_line[container_name]:
                continue
            last_log_line[container_name] = message

            log_buffers[container_name] += message + "\n"

            clients = list(log_connections[container_name])
            send_tasks = [asyncio.create_task(ws.send_text(message)) for ws in clients]
            results = await asyncio.gather(*send_tasks, return_exceptions=True)
            for ws, result in zip(clients, results):
                if isinstance(result, Exception):
                    log_connections[container_name].remove(ws)
    except asyncio.CancelledError:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=3)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
    except Exception as e:
        print(f"Error broadcasting logs for {container_name}: {e}")
    finally:
        if container_name in log_tasks:
            await log_tasks.pop(container_name, None)
        last_log_line.pop(container_name, None)

@router.post("/clear")
async def clear_log_buffers():
    log_buffers.clear()
    return {"status": "cleared"}


@router.get("/sse/{container_name}")
async def logs_sse(request: Request, container_name: str):
    async def event_generator():
        process = await asyncio.create_subprocess_exec(
            'docker', 'logs', '-f', container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        try:
            while True:
                if await request.is_disconnected():
                    break
                line = await process.stdout.readline()
                if not line:
                    await asyncio.sleep(0.1)
                    continue
                message = line.decode(errors="ignore").strip()
                if message == last_log_line[container_name]:
                    continue
                last_log_line[container_name] = message
                log_buffers[container_name] += message + "\n"
                yield {"data": message}
        finally:
            process.terminate()
            await process.wait()
    return EventSourceResponse(event_generator())

