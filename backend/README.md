# Annoy Backend - Data Anonymization API

Backend API for the Quebec Law 25 compliant data anonymization tool.

## Tech Stack

- **Python 3.11+**
- **FastAPI** - Modern, fast web framework
- **PostgreSQL 15** - Database
- **SQLAlchemy** - ORM
- **Alembic** - Database migrations
- **Pydantic v2** - Data validation
- **Pandas** - CSV processing and data manipulation
- **ReportLab** - PDF generation

## Project Structure

```
backend/
├── app/
│   ├── api/v1/              # API endpoints
│   │   └── endpoints/
│   ├── core/                # Core configuration
│   │   ├── config.py       # Settings management
│   │   └── database.py     # DB connection
│   ├── models/              # Data models
│   │   ├── database.py     # SQLAlchemy models
│   │   └── schemas.py      # Pydantic schemas
│   ├── services/            # Business logic
│   │   ├── data_ingestion.py
│   │   ├── detector.py
│   │   ├── anonymizer.py
│   │   ├── risk_evaluator.py
│   │   └── report_generator.py
│   └── main.py             # FastAPI app entry point
├── alembic/                 # Database migrations
├── tests/                   # Test suite
├── uploads/                 # Temporary file storage
├── pyproject.toml          # Poetry dependencies
├── Dockerfile              # Container image
└── README.md               # This file
```

## Getting Started

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- PostgreSQL 15
- Docker & Docker Compose (optional, recommended)

### Option 1: Docker Compose (Recommended)

```bash
# From the project root directory
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Access API docs
open http://localhost:8000/docs
```

### Option 2: Local Development

1. **Install Poetry:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. **Install dependencies:**
```bash
cd backend
poetry install
```

3. **Set up PostgreSQL:**
```bash
# Create database
createdb annoy_db

# Or using psql
psql -U postgres -c "CREATE DATABASE annoy_db;"
```

4. **Configure environment:**
```bash
# Copy example env file
cp ../.env.example ../.env

# Edit .env with your database credentials
```

5. **Run database migrations:**
```bash
poetry run alembic upgrade head
```

6. **Start the development server:**
```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Database Migrations

### Create a new migration

```bash
cd backend
poetry run alembic revision --autogenerate -m "description of changes"
```

### Apply migrations

```bash
poetry run alembic upgrade head
```

### Rollback migration

```bash
poetry run alembic downgrade -1
```

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/api/v1/openapi.json

## Development

### Code Formatting

```bash
# Format code with Black
poetry run black app/

# Lint with Ruff
poetry run ruff check app/
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app tests/

# Run specific test file
poetry run pytest tests/test_detector.py
```

## Environment Variables

See [`.env.example`](../.env.example) for all available configuration options.

Key variables:
- `POSTGRES_SERVER` - Database host
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password
- `POSTGRES_DB` - Database name
- `MAX_UPLOAD_SIZE` - Max file upload size (bytes)
- `UPLOAD_DIR` - Directory for temporary file storage

## API Endpoints (Planned)

### Datasets
- `POST /api/v1/datasets/upload` - Upload CSV file
- `GET /api/v1/datasets/{id}` - Get dataset info
- `GET /api/v1/datasets/{id}/preview` - Preview data
- `DELETE /api/v1/datasets/{id}` - Delete dataset

### Detection
- `POST /api/v1/datasets/{id}/detect` - Detect sensitive data

### Anonymization
- `POST /api/v1/datasets/{id}/anonymize` - Anonymize dataset
- `GET /api/v1/datasets/{id}/download` - Download anonymized CSV

### Risk Assessment
- `GET /api/v1/datasets/{id}/risk-assessment` - Get Law 25 risk assessment

### Reports
- `GET /api/v1/datasets/{id}/report` - Generate PDF compliance report

## License

Proprietary - All rights reserved
