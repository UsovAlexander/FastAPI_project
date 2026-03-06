from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

# Глобальные переменные
engine = None
SessionLocal = None

def get_database_url():
    """Получение DATABASE_URL с подробным логированием"""
    url = os.getenv("DATABASE_URL")
    print(f"🔍 Checking DATABASE_URL: {'Found' if url else 'Not found'}")
    if url:
        # Маскируем пароль для безопасности
        masked_url = url.replace(url.split('@')[0].split(':')[-1], '****') if '@' in url else url
        print(f"📦 DATABASE_URL: {masked_url}")
    else:
        print("❌ DATABASE_URL environment variable is not set")
        print("📋 Available environment variables:")
        for key in os.environ.keys():
            if 'DATABASE' in key or 'DB_' in key or 'POSTGRES' in key:
                print(f"   - {key}")
    return url

def init_db_engine(retries=10, delay=3):
    """Инициализация engine с повторными попытками"""
    global engine, SessionLocal
    
    for attempt in range(retries):
        try:
            print(f"🔄 Database connection attempt {attempt + 1}/{retries}")
            
            url = get_database_url()
            if not url:
                raise ValueError("DATABASE_URL not found")
            
            # Создаем engine
            if "render.com" in url:
                print("⚙️ Using Render.com PostgreSQL configuration")
                engine = create_engine(
                    url,
                    connect_args={"sslmode": "require"},
                    pool_pre_ping=True,
                    pool_recycle=300,
                    echo=True  # Временно включим для отладки
                )
            else:
                engine = create_engine(url, echo=True)
            
            # Проверяем подключение
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            print("✅ Database connection successful")
            
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            return engine
            
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                print(f"⏳ Waiting {delay} seconds before retry...")
                time.sleep(delay)
            else:
                print("❌ All database connection attempts failed")
                raise
    
    return None

def get_db():
    """Генератор для получения сессии БД"""
    global SessionLocal
    if SessionLocal is None:
        init_db_engine()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для создания таблиц
def create_tables():
    """Создание таблиц в базе данных"""
    global engine
    if engine is None:
        engine = init_db_engine()
    
    if engine:
        print("📦 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
    else:
        print("❌ Cannot create tables: no database engine")