import os
import pytest
from jose import jwt
from datetime import timedelta
from fastapi import HTTPException
from app.routers.auth import (
    verify_password, get_password_hash, 
    authenticate_user, create_access_token,
    get_current_user, get_secret_key
)
from app.models import User


def test_password_hashing():
    """Тест хеширования паролей"""
    password = "testpass123"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrongpass", hashed) is False

def test_authenticate_user_success(db_session, test_user):
    """Тест успешной аутентификации"""
    user = authenticate_user(db_session, "testuser", "testpass123")
    assert user is not False
    assert user.username == "testuser"

def test_authenticate_user_wrong_password(db_session, test_user):
    """Тест аутентификации с неверным паролем"""
    user = authenticate_user(db_session, "testuser", "wrongpass")
    assert user is False

def test_authenticate_user_not_found(db_session):
    """Тест аутентификации несуществующего пользователя"""
    user = authenticate_user(db_session, "nonexistent", "pass")
    assert user is False

def test_create_access_token():
    """Тест создания JWT токена"""
    data = {"sub": "testuser"}
    token = create_access_token(data, expires_delta=timedelta(minutes=30))

    payload = jwt.decode(token, os.getenv("SECRET_KEY", "test-secret-key-for-testing"), algorithms=["HS256"])
    assert payload["sub"] == "testuser"
    assert "exp" in payload

def test_create_access_token_default_expiry():
    """Тест создания токена с дефолтным сроком"""
    data = {"sub": "testuser"}
    token = create_access_token(data)
    
    payload = jwt.decode(token, os.getenv("SECRET_KEY", "test-secret-key-for-testing"), algorithms=["HS256"])
    assert payload["sub"] == "testuser"

def test_get_secret_key_success():
    """Тест получения секретного ключа"""
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("SECRET_KEY", "test-key")
        key = get_secret_key()
        assert key == "test-key"

def test_get_secret_key_missing():
    """Тест получения секретного ключа когда он отсутствует"""
    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("SECRET_KEY", raising=False)
        with pytest.raises(HTTPException) as exc_info:
            get_secret_key()
        assert exc_info.value.status_code == 500
        assert "SECRET_KEY not set" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_current_user_success(db_session, test_user, mock_db_connection, mock_secret_key):
    """Тест получения текущего пользователя по токену"""
    token = create_access_token(data={"sub": test_user.username})
    user = await get_current_user(token=token, db=db_session)
    
    assert user.id == test_user.id
    assert user.username == test_user.username

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(db_session, mock_db_connection, mock_secret_key):
    """Тест получения пользователя по невалидному токену"""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token="invalid.token.here", db=db_session)
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user_no_token(db_session, mock_db_connection, mock_secret_key):
    """Тест получения пользователя без токена"""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=None, db=db_session)
    assert exc_info.value.status_code == 401