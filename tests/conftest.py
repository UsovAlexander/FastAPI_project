import pytest
import os
import sys
import asyncio
import kombu

from unittest.mock import Mock, patch
from celery import Celery
from celery.app import app_or_default
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient


os.environ["TESTING"] = "true"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import Base, get_db
from app.models import User, Link
from app.routers.auth import create_access_token, get_password_hash

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Создание тестовой сессии БД"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """Тестовый клиент с переопределенной зависимостью БД"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db

    with patch('app.main.cache') as mock_cache:
        mock_cache.get = Mock()
        mock_cache.set = Mock()
        mock_cache.delete = Mock()
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
    return {"access_token": access_token, "token_type": "bearer"}

@pytest.fixture
def authorized_client(client, user_token):
    """Авторизованный клиент"""
    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {user_token['access_token']}"
    }
    return client

@pytest.fixture
def mock_redis_cache():
    """Мок для Redis кэша"""
    with patch('app.routers.links.cached') as mock_cached:
        mock_cached.return_value = lambda x: x
        yield mock_cached

@pytest.fixture(autouse=True)
def mock_cache_init():
    """Мок для инициализации кэша"""
    with patch('app.main.FastAPICache.init') as mock_init:
        mock_init.return_value = None
        yield mock_init

@pytest.fixture(autouse=True)
def mock_redis_and_celery(monkeypatch):
    """Глобальный мок для Redis и Celery во всех тестах"""
    mock_connection = Mock()
    mock_connection.ensure_connection = Mock()

    monkeypatch.setattr(kombu, "Connection", lambda *args, **kwargs: mock_connection)

    monkeypatch.setattr("app.celery_app.celery_app", Mock())
    monkeypatch.setattr("app.tasks.celery_app", Mock())

@pytest.fixture
def mock_celery_task():
    """Улучшенный мок для Celery задач"""
    with patch('app.routers.links.increment_click_count') as mock_task:
        mock_task.delay = Mock(return_value=None)
        mock_task.apply_async = Mock()
        yield mock_task

@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для асинхронных тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def mock_aiocache(monkeypatch):
    """Глобальный мок для aiocache во всех тестах"""
    mock_cached = Mock()
    mock_cached.return_value = lambda f: f 

    monkeypatch.setattr("aiocache.cached", mock_cached)

    mock_serializer = Mock()
    monkeypatch.setattr("aiocache.serializers.JsonSerializer", lambda: mock_serializer)
    
    yield mock_cached

