from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Не создаем engine сразу, только Base
Base = declarative_base()

# Функция для получения engine (ленивая инициализация)
def get_engine():
    """Создает engine с правильной конфигурацией"""
    TESTING = os.getenv("TESTING", "false").lower() == "true"
    
    if TESTING:
        DATABASE_URL = "sqlite:///./test.db"
        return create_engine(
            DATABASE_URL, 
            connect_args={"check_same_thread": False}
        )
    else:
        DATABASE_URL = os.getenv("DATABASE_URL")
        if not DATABASE_URL:
            # Временно возвращаем None, если нет DATABASE_URL
            # Это позволяет импортировать модуль без ошибок
            return None
        
        # Для PostgreSQL на Render.com
        if "render.com" in DATABASE_URL:
            return create_engine(
                DATABASE_URL,
                connect_args={"sslmode": "require"},
                pool_pre_ping=True,
                pool_recycle=300
            )
        else:
            return create_engine(DATABASE_URL)

# engine будет создан позже
engine = None

def get_session_local():
    """Создает SessionLocal на основе текущего engine"""
    global engine
    if engine is None:
        engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Генератор для получения сессии БД"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для инициализации БД (вызывается в lifespan)
def init_db():
    """Инициализирует подключение к БД и создает таблицы"""
    global engine
    if engine is None:
        engine = get_engine()
    
    if engine is None:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Проверяем подключение
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        raise Exception(f"Failed to connect to database: {e}")
    
    # Создаем таблицы
    Base.metadata.create_all(bind=engine)
    
    return engine