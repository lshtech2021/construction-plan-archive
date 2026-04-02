# Construction Plan Archive

An AI-powered construction plan archive system for ingesting, processing, and semantically searching construction drawing sets.

## Architecture

```
construction-plan-archive/
├── docker-compose.yml       # All infrastructure services
├── .env.example             # Environment variable template
├── README.md
├── frontend/                # React 18 + Vite + TypeScript + Tailwind CSS
│   ├── Dockerfile           # Multi-stage Node 20 build + nginx:alpine serve
│   ├── nginx.conf           # SPA routing + /api proxy to backend
│   ├── src/
│   │   ├── api/             # Typed API client layer
│   │   ├── components/      # Shared UI components + Layout
│   │   └── pages/           # Route-level page components
│   └── vite.config.ts       # Dev server with /api proxy
└── backend/
    ├── Dockerfile           # Multi-stage Python 3.11 build
    ├── requirements.txt
    ├── alembic.ini
    ├── alembic/
    │   ├── env.py
    │   └── versions/
    │       └── 001_initial_schema.py
    └── app/
        ├── main.py          # FastAPI application entry point
        ├── config.py        # Pydantic settings
        ├── database.py      # Async SQLAlchemy engine/session
        ├── dependencies.py  # FastAPI dependency injection
        ├── api/             # Route handlers
        │   ├── health.py
        │   ├── projects.py
        │   ├── documents.py
        │   ├── sheets.py
        │   └── router.py
        ├── models/          # SQLAlchemy ORM models
        │   ├── project.py
        │   ├── document.py
        │   └── sheet.py
        ├── schemas/         # Pydantic request/response schemas
        │   ├── project.py
        │   ├── document.py
        │   └── sheet.py
        ├── services/        # Business logic
        │   ├── storage.py       # MinIO integration
        │   ├── pdf_processor.py # PyMuPDF rendering + text extraction
        │   └── ingestion.py     # Document processing pipeline
        ├── auth/
        │   └── jwt.py       # JWT auth skeleton
        └── utils/
            └── pdf.py       # PDF validation helpers
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript, Tailwind CSS |
| API | FastAPI, Uvicorn |
| Database | PostgreSQL 16, SQLAlchemy (async), Alembic |
| Cache / Queue | Redis 7 |
| Vector DB | Qdrant v1.9.4 |
| Object Storage | MinIO |
| PDF Processing | PyMuPDF (fitz), Pillow |
| Auth | python-jose, passlib |
| Configuration | pydantic-settings |
| Containerisation | Docker, Docker Compose |

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) ≥ 24
- [Docker Compose](https://docs.docker.com/compose/) ≥ 2.20
- [Node.js](https://nodejs.org/) ≥ 20 (for local frontend development)

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/lshtech2021/construction-plan-archive.git
cd construction-plan-archive

# 2. Copy and customise environment variables
cp .env.example .env

# 3. Start all services (including frontend at http://localhost:3000)
docker compose up -d

# 4. Run database migrations (inside the backend container)
docker compose exec backend alembic upgrade head

# 5. Verify the API is healthy
curl http://localhost:8000/api/health
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Frontend Development

```bash
cd frontend
npm install
npm run dev     # starts at http://localhost:5173 with /api proxy to localhost:8000
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` | `cpa` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `cpa_secret` | PostgreSQL password |
| `POSTGRES_DB` | `construction_archive` | Database name |
| `DATABASE_URL` | — | Full async DB URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `QDRANT_HOST` | `qdrant` | Qdrant hostname |
| `QDRANT_HTTP_PORT` | `6333` | Qdrant HTTP port |
| `MINIO_ROOT_USER` | `minioadmin` | MinIO access key |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO secret key |
| `SECRET_KEY` | — | JWT signing secret (change in prod!) |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `PDF_RENDER_DPI` | `300` | DPI for full-res page renders |
| `THUMBNAIL_DPI` | `72` | DPI for thumbnail generation |
| `FRONTEND_PORT` | `3000` | Host port for the frontend container |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Service health check |
| `POST` | `/api/projects` | Create a project |
| `GET` | `/api/projects` | List projects (paginated) |
| `GET` | `/api/projects/{id}` | Get project details |
| `PUT` | `/api/projects/{id}` | Update project |
| `DELETE` | `/api/projects/{id}` | Delete project |
| `POST` | `/api/projects/{id}/documents/upload` | Upload a PDF (async processing) |
| `GET` | `/api/projects/{id}/documents` | List documents for project |
| `GET` | `/api/documents/{id}` | Get document details |
| `GET` | `/api/documents/{id}/status` | Get processing status |
| `GET` | `/api/documents/{id}/sheets` | List sheets (filterable) |
| `GET` | `/api/sheets/{id}` | Get sheet detail |
| `POST` | `/api/search` | Hybrid/semantic/keyword search |
| `POST` | `/api/search/similar` | Find similar sheets |
| `GET` | `/api/search/status` | Search index statistics |

Interactive docs: http://localhost:8000/docs

## Development Commands

```bash
# View logs for a specific service
docker compose logs -f backend
docker compose logs -f frontend

# Restart backend after code changes
docker compose restart backend

# Create a new Alembic migration
docker compose exec backend alembic revision --autogenerate -m "description"

# Apply pending migrations
docker compose exec backend alembic upgrade head

# Access MinIO Console
open http://localhost:9001   # user: minioadmin / pass: minioadmin

# Access PostgreSQL directly
docker compose exec postgres psql -U cpa -d construction_archive

# Stop all services
docker compose down

# Stop and remove all volumes (full reset)
docker compose down -v
```
