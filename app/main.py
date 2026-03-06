import os
import logging
import redis.asyncio as redis

from aiocache import Cache
from aiocache.serializers import JsonSerializer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

from contextlib import asynccontextmanager

from .database import engine, Base
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
        # Создаем таблицы БД
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        if os.getenv("TESTING") == "true":
            cache = Mock()
            logger.info("Using mock cache for testing")
        else:
            redis_url = os.getenv("REDIS_URL")
            if not redis_url:
                logger.warning("REDIS_URL not set, using default")
                redis_url = "redis://localhost:6379/0"
            
            # Исправляем инициализацию Redis
            redis_client = redis.from_url(redis_url, decode_responses=True)
            cache = Cache(Cache.REDIS, endpoint=redis_client, serializer=JsonSerializer())
            logger.info(f"Redis cache initialized")
        
        app.state.cache = cache
        
        # Запускаем scheduler только если не в тестовом режиме
        if os.getenv("TESTING") != "true" and os.getenv("RENDER") != "true":
            scheduler.add_job(run_cleanup_expired, "interval", hours=1)
            scheduler.add_job(run_cleanup_unused, "interval", days=1)
            scheduler.start()
            logger.info("Scheduler started")
        else:
            logger.info("Scheduler not started (testing or Render environment)")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        yield
    finally:
        if scheduler.running:
            try:
                scheduler.shutdown()
                logger.info("Scheduler shutdown")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")

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