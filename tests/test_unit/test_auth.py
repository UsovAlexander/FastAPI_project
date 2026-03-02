import pytest
from jose import jwt
from datetime import timedelta
from app.routers.auth import (
    verify_password, get_password_hash, 
    authenticate_user, create_access_token,
    get_current_user
)
from app.models import User
import os

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

    payload = jwt.decode(token, os.getenv("SECRET_KEY", "your-secret-key-change-in-production"), algorithms=["HS256"])
    assert payload["sub"] == "testuser"
    assert "exp" in payload

def test_create_access_token_default_expiry():
    """Тест создания токена с дефолтным сроком"""
    data = {"sub": "testuser"}
    token = create_access_token(data)
    
    payload = jwt.decode(token, os.getenv("SECRET_KEY", "your-secret-key-change-in-production"), algorithms=["HS256"])
    assert payload["sub"] == "testuser"

@pytest.mark.asyncio
async def test_get_current_user_success(db_session, test_user):
    """Тест получения текущего пользователя по токену"""
    token = create_access_token(data={"sub": test_user.username})
    user = await get_current_user(token=token, db=db_session)
    
    assert user.id == test_user.id
    assert user.username == test_user.username

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(db_session):
    """Тест получения пользователя по невалидному токену"""
    with pytest.raises(Exception):
        await get_current_user(token="invalid.token.here", db=db_session)