from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from manager.controllers import nodes, metrics, logs
from manager.services.metrics_service import metrics_service
from manager.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    await metrics_service.start_collecting()
    yield
    await metrics_service.stop_collecting()

app = FastAPI(lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(nodes.router)
app.include_router(metrics.router)
app.include_router(logs.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}