from app.api.v2 import chips, importers, subscriptions, datasheets

from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(chips.router, prefix="/chips", tags=["Chips"])
api_router.include_router(importers.router, prefix="/import", tags=["Import"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])
api_router.include_router(datasheets.router, prefix="/datasheets", tags=["Datasheets"])


@api_router.get("/")
def api_root():
    return {"message": "You've reached the root of the backend api. Go to /docs for documentation."}

from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v2.chips import router as chips_router
from app.api.v2.importers import router as importers_router
from app.api.v2.subscriptions import router as subscriptions_router
from app.api.v2.datasheets import router as datasheets_router

from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(chips_router, prefix="/chips", tags=["Chips"])
api_router.include_router(importers_router, prefix="/import", tags=["Import"])
api_router.include_router(subscriptions_router, prefix="/subscriptions", tags=["Subscriptions"])
api_router.include_router(datasheets_router, prefix="/datasheets", tags=["Datasheets"])


@api_router.get("/")
def api_root():
    return {"message": "You've reached the root of the backend api. Go to /docs for documentation."}


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

app = FastAPI(
    title="Wireframe Backend", 
    version="0.1.0"
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

app.include_router(api_router)

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
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        workers=1, # Dev mode
    )
