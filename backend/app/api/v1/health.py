from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.base import SessionLocal, settings

router = APIRouter()


@router.get("/health")
def health():
    """Health check - works without database configured."""
    return {
        "status": "ok",
        "service": "caremeds-backend",
        "database_configured": bool(settings.DATABASE_URL),
    }


@router.get("/health/db")
def db_health():
    """Database connectivity diagnostic. Reports actual state without leaking credentials."""
    configured = bool(settings.DATABASE_URL)
    if not configured:
        return {
            "status": "unconfigured",
            "message": "DATABASE_URL not set. Configure backend/.env to test Supabase connection.",
        }
    if SessionLocal is None:
        return {
            "status": "error",
            "message": "Database session not initialized despite DATABASE_URL being set.",
        }
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db.commit()
            return {
                "status": "connected",
                "message": "Successfully connected to database.",
            }
        except SQLAlchemyError as e:
            db.rollback()
            return {
                "status": "error",
                "message": f"Database connection test failed: {type(e).__name__}",
            }
        finally:
            db.close()
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to create database session: {type(e).__name__}",
        }
