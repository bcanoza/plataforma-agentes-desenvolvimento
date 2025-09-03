import logging
from fastapi import APIRouter
import psycopg2
from app.config import settings

router = APIRouter(prefix="/db", tags=["db"])

def get_conn():
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASS
    )

@router.get("/ping")
def ping_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            return {"db": cur.fetchone()[0]}
