from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from manager.controllers import nodes, metrics
from manager.services.metrics_service import metrics_service
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache import FastAPICache

@asynccontextmanager
async def lifespan(app: FastAPI):
    FastAPICache.init(InMemoryBackend())
    await metrics_service.start_collecting()
    yield
    await metrics_service.stop_collecting()

app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nodes.router)
app.include_router(metrics.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}