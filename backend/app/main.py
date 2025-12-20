from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.utils.logging import configure_logging, get_logger
from app.api.middleware.error_handler import exception_handler
from app.api.middleware.tracing import TracingMiddleware
from app.core.exceptions import EDAException
from app.api.routes import analyze, jobs, resume, artifacts
from app.services.database import init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_db()
    await logger.ainfo("application_startup", environment=settings.environment)
    yield
    await logger.ainfo("application_shutdown")


app = FastAPI(
    title="EDA Artifact Generation API",
    description="Automated KiCad Schematic and BOM Generation from PDF Datasheets",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TracingMiddleware)

app.add_exception_handler(EDAException, exception_handler)
app.add_exception_handler(Exception, exception_handler)

app.include_router(analyze.router)
app.include_router(jobs.router)
app.include_router(resume.router)
app.include_router(artifacts.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": settings.environment}
