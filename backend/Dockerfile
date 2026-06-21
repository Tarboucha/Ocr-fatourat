FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies in their own layer so they stay cached across code edits.
# `--no-deps` for the local package isn't used; instead we install deps only via
# a throwaway build, then install the package itself from source without rebuilding deps.
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install --no-cache-dir \
    "fastapi>=0.111" "uvicorn[standard]>=0.30" "sqlalchemy[asyncio]>=2.0" \
    "asyncpg>=0.29" "alembic>=1.13" "python-jose[cryptography]>=3.3" \
    "bcrypt>=4.1" "pydantic>=2.7" "pydantic-settings>=2.3" \
    "python-multipart>=0.0.9" "pillow>=10.3" "pymupdf>=1.24" \
    "email-validator>=2.1"

# Now copy source and install the local package only (deps already satisfied).
COPY . .
RUN pip install --no-deps .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
