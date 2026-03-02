import pytest
from fastapi import status
from datetime import datetime, timedelta

def test_create_short_link_unauthorized(client, mock_celery_task):
    """Тест создания ссылки без авторизации"""
    response = client.post("/links/shorten", json={
        "original_url": "https://example.com"
    })
    
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Not authenticated"

def test_create_link_with_custom_alias(authorized_client):
    """Тест создания ссылки с кастомным алиасом"""
    response = authorized_client.post("/links/shorten", json={
        "original_url": "https://example.com",
        "custom_alias": "myalias123"
    })
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["short_code"] == "myalias123"
    assert data["custom_alias"] == "myalias123"

def test_get_link_stats(client, test_link, mock_redis_cache):
    """Тест получения статистики ссылки"""
    response = client.get(f"/links/{test_link.short_code}/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == test_link.short_code
    assert data["clicks"] == 0
    assert "short_url" in data

def test_update_link(authorized_client, test_link):
    """Тест обновления ссылки"""
    response = authorized_client.put(
        f"/links/{test_link.short_code}",
        json={"original_url": "https://updated.com"}
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["original_url"] == "https://updated.com"

def test_delete_link(authorized_client, test_link):
    """Тест удаления ссылки"""
    response = authorized_client.delete(f"/links/{test_link.short_code}")
    
    assert response.status_code == status.HTTP_200_OK
    assert "message" in response.json()
