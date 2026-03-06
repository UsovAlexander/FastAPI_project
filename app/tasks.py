from .celery_app import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os
from .models import Link

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Настройки для Render.com PostgreSQL
connect_args = {}
if "render.com" in DATABASE_URL:
    connect_args["sslmode"] = "require"

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task
def cleanup_expired_links():
    """Удаление истекших ссылок"""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        expired_links = db.query(Link).filter(
            Link.expires_at <= now,
            Link.is_active == True
        ).all()
        
        for link in expired_links:
            link.is_active = False
        
        db.commit()
        return f"Cleaned up {len(expired_links)} expired links"
    finally:
        db.close()

@celery_app.task
def cleanup_unused_links(days: int = 30):
    """Удаление неиспользуемых ссылок (без переходов за N дней)"""
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        unused_links = db.query(Link).filter(
            Link.last_clicked_at <= cutoff_date,
            Link.is_active == True
        ).all()
        
        for link in unused_links:
            link.is_active = False
        
        db.commit()
        return f"Cleaned up {len(unused_links)} unused links"
    finally:
        db.close()

@celery_app.task
def increment_click_count(link_id: str):
    """Увеличение счетчика кликов"""
    db = SessionLocal()
    try:
        link = db.query(Link).filter(Link.id == link_id).first()
        if link:
            link.clicks += 1
            link.last_clicked_at = datetime.utcnow()
            db.commit()
        return f"Incremented clicks for link {link_id}"
    finally:
        db.close()