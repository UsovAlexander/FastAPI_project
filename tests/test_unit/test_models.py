import pytest
from datetime import datetime, timedelta
from app.models import User, Link
import uuid

def test_create_user(db_session):
    """Тест создания пользователя"""
    user = User(
        email="new@example.com",
        username="newuser",
        hashed_password="hashedpass123"
    )
    db_session.add(user)
    db_session.commit()
    
    assert user.id is not None
    assert isinstance(uuid.UUID(user.id), uuid.UUID)
    assert user.email == "new@example.com"
    assert user.username == "newuser"
    assert user.is_active is True
    assert isinstance(user.created_at, datetime)

def test_user_relationships(db_session, test_user, test_link):
    """Тест связей пользователя с ссылками"""
    user = db_session.query(User).filter(User.id == test_user.id).first()
    assert len(user.links) == 1
    assert user.links[0].id == test_link.id

def test_create_link(db_session, test_user):
    """Тест создания ссылки"""
    link = Link(
        original_url="https://test.com",
        short_code="test123",
        owner_id=test_user.id
    )
    db_session.add(link)
    db_session.commit()
    
    assert link.id is not None
    assert link.short_code == "test123"
    assert link.clicks == 0
    assert link.is_active is True
    assert link.last_clicked_at is None

def test_link_with_expiration(db_session, test_user):
    """Тест ссылки с истекающим сроком"""
    expires_at = datetime.utcnow() + timedelta(days=7)
    link = Link(
        original_url="https://test.com",
        short_code="expire123",
        owner_id=test_user.id,
        expires_at=expires_at
    )
    db_session.add(link)
    db_session.commit()
    
    assert link.expires_at == expires_at
    assert link.is_active is True

def test_link_with_custom_alias(db_session, test_user):
    """Тест ссылки с кастомным алиасом"""
    link = Link(
        original_url="https://test.com",
        short_code="custom123",
        custom_alias="myalias",
        owner_id=test_user.id
    )
    db_session.add(link)
    db_session.commit()
    
    assert link.custom_alias == "myalias"
    assert link.short_code == "custom123"