import os
import logging
import time
import redis.asyncio as redis

from aiocache import Cache
from aiocache.serializers import JsonSerializer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager
from sqlalchemy import text

from .database import init_db, get_db, engine
from .routers import links, auth
from .tasks import cleanup_expired_links, cleanup_unused_links
from unittest.mock import Mock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

scheduler = BackgroundScheduler()
cache = None

def run_cleanup_expired():
    try:
        cleanup_expired_links.delay()
        logger.info("Scheduled expired links cleanup")
    except Exception as e:
        logger.error(f"Error scheduling expired links cleanup: {e}")

def run_cleanup_unused():
    try:
        cleanup_unused_links.delay(30)
        logger.info("Scheduled unused links cleanup")
    except Exception as e:
        logger.error(f"Error scheduling unused links cleanup: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan контекстный менеджер для управления ресурсами"""
    global cache
    
    try:
        # Инициализируем БД с retry логикой
        max_retries = 5
        retry_count = 0
        db_initialized = False
        
        while retry_count < max_retries and not db_initialized:
            try:
                logger.info(f"Initializing database (attempt {retry_count + 1}/{max_retries})...")
                
                # Проверяем наличие DATABASE_URL
                db_url = os.getenv("DATABASE_URL")
                if not db_url:
                    logger.error("DATABASE_URL not set")
                    raise ValueError("DATABASE_URL environment variable is not set")
                
                logger.info(f"DATABASE_URL found: {db_url[:20]}...")  # Логируем начало URL для отладки
                
                # Инициализируем БД
                init_db()
                logger.info("Database initialized successfully")
                db_initialized = True
                
            except Exception as e:
                retry_count += 1
                if retry_count == max_retries:
                    logger.error(f"Failed to initialize database after {max_retries} attempts: {e}")
                    raise
                logger.warning(f"Database initialization attempt {retry_count} failed, retrying in 5 seconds...")
                time.sleep(5)
        
        # Инициализация Redis
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                logger.info(f"Initializing Redis...")
                redis_client = redis.from_url(redis_url, decode_responses=True)
                await redis_client.ping()
                cache = Cache(Cache.REDIS, endpoint=redis_client, serializer=JsonSerializer())
                app.state.cache = cache
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                cache = None
                app.state.cache = None
        else:
            logger.warning("REDIS_URL not set, cache disabled")
            cache = None
            app.state.cache = None
        
        # Запускаем scheduler (опционально)
        if os.getenv("ENABLE_SCHEDULER", "false").lower() == "true":
            scheduler.add_job(run_cleanup_expired, "interval", hours=1)
            scheduler.add_job(run_cleanup_unused, "interval", days=1)
            scheduler.start()
            logger.info("Scheduler started")
        
        yield
        
    except Exception as e:
        logger.error(f"Fatal error during startup: {e}")
        raise  # Пробрасываем ошибку, чтобы Render увидел, что деплой не удался
    finally:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("Scheduler shutdown")

app = FastAPI(
    title="URL Shortener Service", 
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(links.router)

@app.get("/")
async def root():
    base_url = os.getenv("BASE_URL", "https://your-app.onrender.com")
    return {
        "message": "URL Shortener Service",
        "version": "1.0.0",
        "base_url": base_url,
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "register": "POST /register",
            "login": "POST /token",
            "create_link": "POST /links/shorten",
            "redirect": "GET /{short_code}",
            "stats": "GET /links/{short_code}/stats",
            "search": "GET /links/search",
            "delete": "DELETE /links/{short_code}",
            "update": "PUT /links/{short_code}"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)