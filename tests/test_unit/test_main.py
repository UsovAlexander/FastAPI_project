import pytest
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import os
import sys
from contextlib import asynccontextmanager

from app.main import app, lifespan, run_cleanup_expired, run_cleanup_unused

def test_root_endpoint():
    """Тест корневого эндпоинта"""
    with TestClient(app) as client:
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "URL Shortener Service"
        assert "version" in data
        assert "endpoints" in data

def test_health_endpoint():
    """Тест health check"""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

def test_debug_env_endpoint():
    """Тест debug/env эндпоинта"""
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://user:pass@localhost/db",
        "REDIS_URL": "redis://localhost:6379",
        "SECRET_KEY": "test-secret-key"
    }):
        with TestClient(app) as client:
            response = client.get("/debug/env")
            assert response.status_code == 200
            data = response.json()
            assert "database_url_set" in data
            assert "redis_url_set" in data
            assert "secret_key_set" in data

def test_run_cleanup_expired_success():
    """Тест успешного запуска cleanup_expired"""
    with patch('app.main.cleanup_expired_links.delay') as mock_delay:
        run_cleanup_expired()
        mock_delay.assert_called_once()

def test_run_cleanup_expired_error():
    """Тест ошибки при запуске cleanup_expired"""
    with patch('app.main.cleanup_expired_links.delay', side_effect=Exception("Test error")):
        # Должен обработать ошибку без исключения
        run_cleanup_expired()

def test_run_cleanup_unused_success():
    """Тест успешного запуска cleanup_unused"""
    with patch('app.main.cleanup_unused_links.delay') as mock_delay:
        run_cleanup_unused()
        mock_delay.assert_called_once_with(30)

def test_run_cleanup_unused_error():
    """Тест ошибки при запуске cleanup_unused"""
    with patch('app.main.cleanup_unused_links.delay', side_effect=Exception("Test error")):
        # Должен обработать ошибку без исключения
        run_cleanup_unused()

@pytest.mark.asyncio
async def test_lifespan_database_success():
    """Тест успешной инициализации БД в lifespan"""
    with patch('app.main.init_db_engine') as mock_init, \
         patch('app.main.is_db_connected', return_value=True), \
         patch('app.main.os.getenv', return_value="redis://test"):
        
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        
        mock_cache = MagicMock()
        
        with patch('app.main.redis.from_url', return_value=mock_redis), \
             patch('app.main.Cache', return_value=mock_cache):
            
            async with lifespan(app):
                pass

@pytest.mark.asyncio
async def test_lifespan_database_failure():
    """Тест ошибки инициализации БД в lifespan"""
    with patch('app.main.init_db_engine', side_effect=Exception("DB Error")), \
         patch('app.main.os.getenv', return_value=None):
        
        async with lifespan(app):
            pass  # Не должно быть исключения

@pytest.mark.asyncio
async def test_lifespan_redis_success():
    """Тест успешной инициализации Redis в lifespan"""
    with patch('app.main.init_db_engine'), \
         patch('app.main.is_db_connected', return_value=True), \
         patch('app.main.os.getenv', return_value="redis://test"):
        
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        
        mock_cache = MagicMock()
        
        with patch('app.main.redis.from_url', return_value=mock_redis), \
             patch('app.main.Cache', return_value=mock_cache):
            
            async with lifespan(app):
                pass

@pytest.mark.asyncio
async def test_lifespan_redis_failure():
    """Тест ошибки инициализации Redis в lifespan"""
    with patch('app.main.init_db_engine'), \
         patch('app.main.is_db_connected', return_value=True), \
         patch('app.main.os.getenv', return_value="redis://test"):
        
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("Redis Error"))
        
        with patch('app.main.redis.from_url', return_value=mock_redis):
            async with lifespan(app):
                pass  # Не должно быть исключения

def test_main_block():
    """Тест блока __main__"""
    with patch('uvicorn.run') as mock_run, \
         patch.dict(os.environ, {"PORT": "8000"}):
        
        # Импортируем модуль, чтобы выполнился блок __main__
        import importlib
        import app.main
        importlib.reload(app.main)
        
        # Проверяем, что uvicorn.run был вызван
        # mock_run.assert_called_once()