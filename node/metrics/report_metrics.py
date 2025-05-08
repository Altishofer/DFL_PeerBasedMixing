



import asyncio
import httpx
from node.metrics.node_metrics import Metrics

async def push_metrics_periodically(controller_url: str, interval: float = 5.0):
    metrics = Metrics()
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(interval)
            history = metrics.get_history()
            try:
                await client.post(f"{controller_url}/receive_metrics", json=history)
            except Exception as e:
                print(f"Failed to push metrics: {e}")


@app.on_event("startup")
async def start_metrics_push():
    asyncio.create_task(push_metrics_periodically("http://controller:8000"))
