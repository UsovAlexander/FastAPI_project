import pytest
from fastapi import status

def test_register_success(client, db_session):
    """Тест успешной регистрации"""
    response = client.post("/register", json={
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "password123"
    })
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert "id" in data
    assert "created_at" in data

def test_register_duplicate_email(client, test_user):
    """Тест регистрации с существующим email"""
    response = client.post("/register", json={
        "email": "test@example.com",
        "username": "another",
        "password": "password123"
    })
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"].lower()

def test_register_duplicate_username(client, test_user):
    """Тест регистрации с существующим username"""
    response = client.post("/register", json={
        "email": "another@example.com",
        "username": "testuser",
        "password": "password123"
    })
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"].lower()

def test_login_success(client, test_user):
    """Тест успешного логина"""
    response = client.post("/token", data={
        "username": "testuser",
        "password": "testpass123"
    })
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client, test_user):
    """Тест логина с неверным паролем"""
    response = client.post("/token", data={
        "username": "testuser",
        "password": "wrongpass"
    })
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_login_nonexistent_user(client):
    """Тест логина несуществующего пользователя"""
    response = client.post("/token", data={
        "username": "nonexistent",
        "password": "pass123"
    })
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_current_user(authorized_client):
    """Тест получения информации о текущем пользователе"""
    response = authorized_client.get("/users/me")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"

def test_get_current_user_unauthorized(client):
    """Тест получения информации без токена"""
    response = client.get("/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED