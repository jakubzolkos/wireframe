from pathlib import Path
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from wireframe.api.ingestor.router import router as ingestor_router
from wireframe.api.generator.router import router as generator_router
from wireframe.api.auth.router import router as auth_router
from wireframe.api.chips.router import router as chips_router
from wireframe.api.jobs.router import router as jobs_router
from wireframe.utils.redis import get_redis_pool

# Setup structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.arq_pool = await get_redis_pool()
    yield
    await app.state.arq_pool.close()

app = FastAPI(
    title="Wireframe Backend", 
    version="0.1.0",
    lifespan=lifespan
)

# CORS Configuration
origins = [
    "https://autopcb.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "https://dev.autopcb.app",
    "https://prod.autopcb.app",
    "https://wireframe.app", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestor_router, prefix="/ingestor", tags=["Ingestor"])
app.include_router(generator_router, prefix="/generator", tags=["Generator"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(chips_router, prefix="/chips", tags=["Chips"])
app.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


class NoCacheStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs):
        self.cachecontrol = "no-cache"
        self.pragma = "no-cache"
        super().__init__(*args, **kwargs)

    def file_response(self, *args, **kwargs):
        resp = super().file_response(*args, **kwargs)
        resp.headers.setdefault("Cache-Control", self.cachecontrol)
        resp.headers.setdefault("Pragma", self.pragma)
        return resp

# Check if static directory exists before mounting
static_dir = Path("app/api/static")
if static_dir.exists():
    app.mount("/static", NoCacheStaticFiles(directory=str(static_dir)), name="static")

if __name__ == "__main__":
    uvicorn.run(
        "wireframe.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        workers=1, 
    )
