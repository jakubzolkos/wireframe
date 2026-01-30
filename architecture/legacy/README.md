# Backend Setup

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package management and virtual environment handling.

## Local Development (Windows)

For local development on Windows, use a virtual environment to isolate dependencies.

### Prerequisites

Install `uv` (if not already installed):

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Or with pip:
```bash
pip install uv
```

### Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment with uv:**
   ```bash
   uv venv
   .venv\Scripts\activate  # PowerShell
   # or
   .venv\Scripts\activate.bat  # CMD
   ```

3. **Install dependencies:**
   ```bash
   uv pip install -e .
   ```

   Or use uv's sync command (recommended):
   ```bash
   uv sync
   ```

## Docker Deployment

For Docker deployment, the Dockerfile automatically uses `uv` to install dependencies. No virtual environment is needed since the container is isolated.

The Dockerfile:
- Uses `uv` for fast dependency installation
- Installs from `pyproject.toml` (not `requirements.txt`)
- Optimizes Docker layer caching by copying `pyproject.toml` first

**Build and run:**
```bash
docker build -t wireframe-backend .
docker run -p 8000:8000 wireframe-backend
```

## Development Workflow

- **Install a new package:**
  ```bash
  uv add package-name
  ```

- **Remove a package:**
  ```bash
  uv remove package-name
  ```

- **Update dependencies:**
  ```bash
  uv sync --upgrade
  ```

- **Run commands in the virtual environment:**
  ```bash
  uv run python script.py
  uv run pytest
  ```

## Alternative: Manual Virtual Environment

If you prefer to use Python's built-in venv:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

