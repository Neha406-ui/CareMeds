"""
Project Overview Script for CareMeds
===================================

This script prints a concise, human‑readable description of the entire CareMeds
application – both the **backend** (FastAPI) and the **frontend** (React + Vite).
It can be executed with ``python project_overview.py`` from the repository root.

The output is formatted as Markdown so you can pipe it directly to a ``README.md``
or view it in the console.
"""

import os
import json
from pathlib import Path

def list_files(root: Path, depth: int = 3) -> dict:
    """Recursively list files up to *depth* levels for a quick tree view."""
    tree = {}
    if depth < 0:
        return tree
    for entry in sorted(root.iterdir()):
        if entry.is_dir():
            tree[entry.name + "/"] = list_files(entry, depth - 1)
        else:
            tree[entry.name] = None
    return tree

def format_tree(tree: dict, prefix: str = "") -> str:
    lines = []
    for i, (name, subtree) in enumerate(tree.items()):
        connector = "├─ " if i < len(tree) - 1 else "└─ "
        lines.append(f"{prefix}{connector}{name}")
        if subtree is not None:
            extension = "│   " if i < len(tree) - 1 else "    "
            lines.extend(format_tree(subtree, prefix + extension))
    return "\n".join(lines)

def main():
    repo_root = Path(__file__).parent
    print("# CareMeds – Medication Management System\n")
    print("## Project Structure (truncated view)\n")
    tree = list_files(repo_root)
    print("```")
    print(format_tree(tree))
    print("```")

    print("## Backend – FastAPI\n")
    print("* **Language**: Python 3.13\n* **Framework**: FastAPI (async‑ready)\n* **Database**: PostgreSQL (SQLAlchemy ORM)\n* **Authentication**: OAuth2 password flow with JWT bearer tokens\n* **Roles**: `admin`, `doctor`, `caretaker`, `resident`, `family_member`\n")
    print("### Key Packages (``backend/requirements.txt``)\n")
    req_path = repo_root / "backend" / "requirements.txt"
    if req_path.exists():
        print("```")
        print(req_path.read_text())
        print("```")
    else:
        print("*(requirements file not found)*")

    print("### Core Modules\n")
    modules = [
        "app/main.py – FastAPI app creation, CORS, API prefix\n",
        "app/api/v1/auth.py – login, token generation, self‑registration, admin user CRUD\n",
        "app/api/v1/residents.py – CRUD for resident profiles\n",
        "app/api/v1/prescriptions.py – medicine catalog, prescription CRUD, status handling\n",
        "app/models/ – SQLAlchemy model definitions (User, Resident, Medicine, Prescription, …)\n",
        "app/schemas/ – Pydantic request/response schemas\n",
        "app/core/security.py – password hashing (bcrypt) and JWT utilities\n",
        "app/db/base.py – SQLAlchemy session handling\n",
        "app/bootstrap_admin.py – helper to create the first admin if missing\n",
        "seed.py – idempotent script that populates dummy data for every role\n",
    ]
    for m in modules:
        print(f"* {m}")

    print("## Frontend – React (Vite)\n")
    print("* **Language**: JavaScript (ES2022)\n* **Framework**: React 18 with functional components\n* **Bundler**: Vite – fast hot‑module reloading\n* **Styling**: Vanilla CSS with a modern, premium design system (glassmorphism, gradients, micro‑animations)\n* **State Management**: Local component state + React Context for auth token\n")
    print("### Important UI Pages (``frontend/src/App.jsx``)\n")
    pages = [
        "LoginPage – username / password entry, link to Sign Up\n",
        "SignUpPage – self‑registration for `family_member` role\n",
        "DashboardPage – quick stats, navigation sidebar\n",
        "ResidentsPage – list / create / edit resident profiles\n",
        "MedicinesPage – view / add medicines to the catalog\n",
        "PrescriptionsPage – view active prescriptions, create new ones\n",
        "DoseSchedulePage – (placeholder) schedule view for a selected date\n",
        "OperationsPage – inventory, notifications, escalations, handovers, audit logs\n",
        "AccessPage – family contact request handling\n",
        "SettingsPage – user profile & preferences\n",
    ]
    for p in pages:
        print(f"* {p}")

    print("## Authentication Flow\n")
    print("1. User enters credentials on the login form.\n2. Frontend calls ``POST /api/auth/token`` with ``username`` and ``password``.\n3. Backend validates, issues a JWT (``access_token``) and returns ``token_type: bearer``.\n4. Frontend stores the token (in memory / local storage) and includes it as ``Authorization: Bearer <token>`` on subsequent API calls.\n5. ``GET /api/auth/me`` returns the current user profile – used to drive role‑based UI rendering.\n")

    print("## Seed Data (``seed.py``)\n")
    print("Running ``python seed.py`` creates a realistic demo dataset without touching any existing rows:\n")
    print("* 1 admin (already present)\n* 2 doctors\n* 3 caretakers\n* 5 residents (each with a linked user)\n* 3 family members linked to residents\n* 10 medicines\n* 12 prescriptions (active, discontinued, on‑hold)\n* Caretaker‑resident assignments\n* Family‑resident consent links\n")
    print("The script is **idempotent** – it checks for existing usernames/medicine names before inserting, so you can re‑run it safely.\n")

    print("## How to Run the Project\n")
    print("```bash
# 1. Install backend dependencies (inside the backend folder)
cd d:/MediCare/backend
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt

# 2. Apply migrations (Alembic) – the initial migration is already present
alembic upgrade head

# 3. (Optional) Seed the database with demo data
python seed.py

# 4. Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. Install frontend dependencies (inside the frontend folder)
cd d:/MediCare/frontend
npm install

# 6. Start the Vite dev server
npm run dev   # defaults to http://localhost:5173
```\n")

    print("## Extending the Project\n")
    print("* Add new FastAPI routers under ``app/api/v1`` and expose them in ``app/api/v1/__init__.py``.\n* Create corresponding React components/pages and wire them into ``App.jsx``.\n* Update ``seed.py`` with helper functions to populate any new tables you add.\n* Run ``alembic revision --autogenerate -m "your description"`` to create migration scripts for schema changes.\n")

    print("---\nGenerated by ``project_overview.py`` – keep this file in the repo for quick reference or to regenerate the README whenever the structure changes.")

if __name__ == "__main__":
    main()
