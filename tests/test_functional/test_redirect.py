import pytest
from fastapi import status
from unittest.mock import patch
from datetime import datetime, timedelta

def test_redirect_success(client, test_link, mock_celery_task):
    """Тест успешного редиректа"""
    response = client.get(f"/{test_link.short_code}", follow_redirects=False)
    
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers["location"] == test_link.original_url
    mock_celery_task.delay.assert_called_once_with(test_link.id)

def test_redirect_with_custom_alias(client, db_session, test_user):
    """Тест редиректа по кастомному алиасу"""
    from app.models import Link
    link = Link(
        original_url="https://alias.com",
        short_code="normal123",
        custom_alias="special",
        owner_id=test_user.id
    )
    db_session.add(link)
    db_session.commit()
    
    response = client.get("/special", follow_redirects=False)
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
    assert response.headers["location"] == "https://alias.com"

def test_redirect_not_found(client):
    """Тест редиректа по несуществующей ссылке"""
    response = client.get("/nonexistent")
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_redirect_expired_link(client, db_session, test_user):
    """Тест редиректа по просроченной ссылке"""
    from app.models import Link
    from datetime import datetime, timedelta
    
    expired_link = Link(
        original_url="https://expired.com",
        short_code="expired",
        owner_id=test_user.id,
        expires_at=datetime.utcnow() - timedelta(days=1),
        is_active=True
    )
    db_session.add(expired_link)
    db_session.commit()
    
    response = client.get("/expired")
    assert response.status_code == status.HTTP_410_GONE