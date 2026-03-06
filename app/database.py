from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

Base = declarative_base()

# Глобальные переменные
engine = None
SessionLocal = None

def get_database_url():
    """Получение DATABASE_URL с подробным логированием"""
    url = os.getenv("DATABASE_URL")
    logger.info(f"Checking DATABASE_URL: {'Found' if url else 'Not found'}")
    
    # Также проверяем другие возможные переменные
    if not url:
        url = os.getenv("POSTGRES_URL")
        if url:
            logger.info("Using POSTGRES_URL instead")
    
    if not url:
        url = os.getenv("RENDER_DATABASE_URL")
        if url:
            logger.info("Using RENDER_DATABASE_URL instead")
    
    return url

def init_db_engine(retries=3, delay=2):
    """Инициализация engine с повторными попытками"""
    global engine, SessionLocal
    
    for attempt in range(retries):
        try:
            logger.info(f"Database connection attempt {attempt + 1}/{retries}")
            
            url = get_database_url()
            if not url:
                # Если нет URL, просто логируем и возвращаем None
                # Не падаем с ошибкой, чтобы приложение могло запуститься
                logger.warning("DATABASE_URL not found, skipping database initialization")
                return None
            
            logger.info(f"Creating database engine...")
            
            # Создаем engine
            if "render.com" in url or "postgres" in url:
                logger.info("Using PostgreSQL configuration")
                engine = create_engine(
                    url,
                    connect_args={"sslmode": "require"} if "render.com" in url else {},
                    pool_pre_ping=True,
                    pool_recycle=300,
                    echo=False  # Отключаем echo для продакшена
                )
            else:
                engine = create_engine(url, echo=False)
            
            # Проверяем подключение
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            logger.info("✅ Database connection successful")
            
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            
            # Создаем таблицы
            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables created successfully")
            
            return engine
            
        except Exception as e:
            logger.error(f"❌ Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                logger.info(f"Waiting {delay} seconds before retry...")
                time.sleep(delay)
            else:
                logger.error("All database connection attempts failed")
                # Возвращаем None вместо raise, чтобы приложение могло запуститься
                return None
    
    return None

def get_db():
    """Генератор для получения сессии БД"""
    global SessionLocal, engine
    
    # Если engine еще не инициализирован, пробуем инициализировать
    if engine is None:
        logger.info("Database engine not initialized, initializing now...")
        init_db_engine()
    
    # Если после инициализации все еще нет SessionLocal, возвращаем заглушку
    if SessionLocal is None:
        logger.error("Cannot create database session - database not available")
        # Возвращаем заглушку, чтобы приложение не падало
        class DummyDB:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def query(self, *args, **kwargs):
                return []
            def add(self, *args):
                pass
            def commit(self):
                pass
            def refresh(self, *args):
                pass
            def close(self):
                pass
        
        yield DummyDB()
        return
    
    # Нормальная работа с БД
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для проверки статуса БД
def is_db_connected():
    """Проверка подключения к БД"""
    global engine
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        return True
    except:
        return False