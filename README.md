# CareMeds

CareMeds: An Intelligent Medication Management, Adherence Monitoring, and Smart Reminder System for Senior Citizens in Old-Age Homes.

## Phase 1 Foundation

This repository contains the initial foundation for CareMeds (React + Vite frontend, FastAPI backend, Supabase PostgreSQL).

## Prerequisites
- Python 3.10+ (Windows)
- Node.js 18+ (LTS recommended)
- Git

## 1) Clone and navigate
`powershell
cd D:\MediCare  # or your workspace
`

## 2) Backend setup

Create and activate Python virtual environment:
`powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
`

Install dependencies:
`powershell
pip install -r requirements.txt
`

Configure environment variables:
`powershell
Copy-Item .env.example .env
`

Edit .env and set DATABASE_URL to your Supabase PostgreSQL connection string (see Section 5).

## 3) Supabase PostgreSQL configuration

### Create a Supabase project
1. Go to https://supabase.com/ and sign in
2. Click "New Project" and choose organization/region
3. Set project name and password (note the password)

### Get database connection details
Supabase provides connection strings. For Phase 1, use the "Connection string" (URI) for PostgreSQL. The recommended format is:
postgresql+psycopg2://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres

Where YOUR_PROJECT_REF is your project reference ID (visible in Project Settings > Database).

### Configure DATABASE_URL
Update ackend/.env:
`	ext
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
`
- Do not commit .env files.
- Use the correct password from project creation.
- Supabase also offers pooled connections (pgbouncer) - connection pooling is appropriate in managed deployments; direct connection works for local/dev and migrations.

### Run Alembic migrations (when schema exists)
Migrations are configured to read DATABASE_URL from environment. For Phase 1, the initial schema is minimal; run head if migrations are present:
`powershell
# From backend directory with venv active
alembic upgrade head
`
Note: No schema migrations are required for Phase 1 health checks.

## 4) Run backend
From ackend with venv active:
`powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
`

## 5) Frontend setup

Open new PowerShell terminal:
`powershell
cd frontend
npm install
`

Configure environment variables:
`powershell
Copy-Item .env.example .env
`

Edit rontend/.env if needed (default is fine for local):
`	ext
VITE_API_BASE_URL=http://localhost:8000/api
`

Start dev server:
`powershell
npm run dev
`

## 6) API endpoints
- Health (works without DB): GET http://localhost:8000/api/health
- DB connectivity diagnostic: GET http://localhost:8000/api/health/db

## 7) Tests

Backend tests (from backend with venv active):
`powershell
python -m pytest tests/test_health.py tests/test_db_connectivity.py -v
`

Frontend tests (from frontend):
`powershell
npm test
`

Build frontend (from frontend):
`powershell
npm run build
`

## 8) Notes
- Health endpoint works without Supabase configured.
- DB diagnostic reports unconfigured if DATABASE_URL not set, or actual connection status if configured (without exposing credentials).
- No fake data created in Phase 1. This is foundation only.
