import pytest
import os
import sys
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import Base, get_db, init_db_engine, is_db_connected, engine as global_engine
from app.models import User, Link
from app.routers.auth import create_access_token, get_password_hash, get_secret_key
from app.tasks import celery_app

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def mock_db_connection():
    """Автоматически мокаем подключение к БД для всех тестов"""
    with patch('app.database.is_db_connected', return_value=True), \
         patch('app.routers.auth.is_db_connected', return_value=True), \
         patch('app.routers.links.is_db_connected', return_value=True):
        yield

@pytest.fixture(scope="function")
def db_session():
    """Создание тестовой сессии БД"""
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    

    from app.database import engine as db_engine
    original_engine = db_engine
    import app.database
    app.database.engine = engine
    app.database.SessionLocal = TestingSessionLocal
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        app.database.engine = original_engine

@pytest.fixture(scope="function")
def client(db_session):
    """Тестовый клиент с переопределенной зависимостью БД"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db

    with patch('app.main.redis.from_url') as mock_redis:
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock(return_value=True)
        mock_redis.return_value = mock_redis_client

        with patch('app.main.Cache') as mock_cache:
            mock_cache.return_value = Mock()
            
            with TestClient(app) as test_client:
                yield test_client
    
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db_session):
    """Создание тестового пользователя"""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpass123")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_link(db_session, test_user):
    """Создание тестовой ссылки"""
    link = Link(
        original_url="https://example.com",
        short_code="abc123",
        owner_id=test_user.id,
        clicks=0
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)
    return link

@pytest.fixture
def another_user(db_session):
    """Создание другого тестового пользователя"""
    user = User(
        email="another@example.com",
        username="anotheruser",
        hashed_password=get_password_hash("anotherpass123")
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def another_link(db_session, another_user):
    """Создание тестовой ссылки другого пользователя"""
    link = Link(
        original_url="https://another.com",
        short_code="xyz789",
        owner_id=another_user.id,
        clicks=5
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)
    return link

@pytest.fixture
def user_token(test_user):
    """Создание токена для тестового пользователя"""
    access_token = create_access_token(data={"sub": test_user.username})
    return access_token

@pytest.fixture
def authorized_client(client, user_token):
    """Авторизованный клиент"""
    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {user_token}"
    }
    return client

@pytest.fixture
def mock_redis_cache():
    """Мок для Redis кэша"""
    with patch('app.routers.links.cached') as mock_cached:
        mock_cached.return_value = lambda x: x
        yield mock_cached

@pytest.fixture
def mock_celery_task():
    """Мок для Celery задач"""
    with patch('app.routers.links.increment_click_count') as mock_task:
        mock_task.delay = Mock(return_value=None)
        yield mock_task

@pytest.fixture(scope="function")
def mock_secret_key():
    """Мок для SECRET_KEY"""
    with patch('app.routers.auth.get_secret_key', return_value="test-secret-key"):
        yield

@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для асинхронных тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()