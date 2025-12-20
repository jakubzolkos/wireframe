# EDA Artifact Generation Backend

Automated KiCad Schematic and BOM Generation from PDF Datasheets using LangGraph multi-agent orchestration.

## Architecture

This backend implements a cyclic multi-agent LangGraph system that processes PDF datasheets through seven orchestrated nodes:

1. **Ingestion Supervisor** - Routes chunks to appropriate agents
2. **Vision Agent** - Extracts netlist from schematic images
3. **Constants Miner** - Extracts electrical characteristics from tables
4. **Equation Extractor** - Extracts design equations from application notes
5. **Math Engineer** - Generates Python code to solve equations
6. **Executor** - Executes code in secure E2B sandbox
7. **HITL Node** - Handles missing variable requests

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (copy `.env.example` to `.env`):
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/eda_db
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
E2B_API_KEY=...
# ... other variables
```

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start the server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

- `POST /analyze` - Upload and analyze a PDF datasheet
- `GET /jobs/{job_id}` - Get job status and design data
- `GET /jobs/{job_id}/stream` - Stream real-time processing updates (SSE)
- `POST /jobs/{job_id}/resume` - Resume job with missing variables
- `GET /jobs/{job_id}/artifacts/schematic.kicad_sch` - Download KiCad schematic
- `GET /jobs/{job_id}/artifacts/bom.csv` - Download BOM CSV

## Development

- Linting: `ruff check .`
- Formatting: `ruff format .`
- Type checking: `mypy app`
- Tests: `pytest`

## Dependencies

- FastAPI - Async web framework
- LangGraph - Multi-agent orchestration
- Marker-pdf - PDF parsing (primary)
- E2B - Secure code execution sandbox
- SQLAlchemy 2.0 - Async ORM
- Pydantic V2 - Data validation
