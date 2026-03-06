import os
import logging
import sys
import time
import redis.asyncio as redis

from aiocache import Cache
from aiocache.serializers import JsonSerializer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

load_dotenv()

from .database import init_db_engine, is_db_connected, get_db
from .routers import links, auth
from .tasks import cleanup_expired_links, cleanup_unused_links

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
        # Пробуем инициализировать БД, но не падаем если не получается
        logger.info("Attempting to initialize database...")
        try:
            init_db_engine(retries=3, delay=2)
            if is_db_connected():
                logger.info("✅ Database connected successfully")
            else:
                logger.warning("⚠️ Database not connected - app will run in limited mode")
        except Exception as e:
            logger.error(f"❌ Database initialization error: {e}")
            logger.warning("Continuing without database - some features may not work")
        
        # Инициализация Redis
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                logger.info("Initializing Redis...")
                redis_client = redis.from_url(redis_url, decode_responses=True)
                await redis_client.ping()
                cache = Cache(Cache.REDIS, endpoint=redis_client, serializer=JsonSerializer())
                app.state.cache = cache
                logger.info("✅ Redis cache initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to connect to Redis: {e}")
                cache = None
                app.state.cache = None
        else:
            logger.warning("⚠️ REDIS_URL not set, cache disabled")
            cache = None
            app.state.cache = None
        
        yield
        
    except Exception as e:
        logger.error(f"💥 Error during startup: {e}")
        yield
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
    db_status = "connected" if is_db_connected() else "disconnected"
    redis_status = "connected" if cache else "disconnected"
    
    base_url = os.getenv("BASE_URL", "https://your-app.onrender.com")
    
    return {
        "message": "URL Shortener Service",
        "version": "1.0.0",
        "status": {
            "database": db_status,
            "redis": redis_status
        },
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
    db_status = is_db_connected()
    redis_status = cache is not None
    
    return {
        "status": "healthy" if db_status and redis_status else "degraded",
        "database": "connected" if db_status else "disconnected",
        "redis": "connected" if redis_status else "disconnected"
    }

@app.get("/debug/env")
async def debug_env():
    """Отладка переменных окружения"""
    env_vars = {}
    for key in os.environ.keys():
        if 'DATABASE' in key or 'REDIS' in key or 'POSTGRES' in key:
            value = os.environ[key]
            # Маскируем пароль
            if 'postgresql://' in value and '@' in value:
                try:
                    parts = value.split('@')
                    credentials = parts[0].split('://')[1].split(':')
                    if len(credentials) > 1:
                        masked = f"{credentials[0]}:****@{parts[1]}"
                        value = f"postgresql://{masked}"
                except:
                    pass
            env_vars[key] = value
    
    return {
        "available_env_vars": list(env_vars.keys()),
        "values": env_vars,
        "database_connected": is_db_connected(),
        "redis_connected": cache is not None
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)