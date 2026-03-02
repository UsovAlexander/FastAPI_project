import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from app.tasks import cleanup_expired_links, cleanup_unused_links, increment_click_count
from app.models import Link

def test_cleanup_expired_links(db_session, test_user):
    """Тест очистки истекших ссылок"""

    expired_link = Link(
        original_url="https://expired.com",
        short_code="expired",
        owner_id=test_user.id,
        expires_at=datetime.utcnow() - timedelta(days=1),
        is_active=True
    )
    db_session.add(expired_link)
    db_session.commit()

    link_id = expired_link.id

    with patch('app.tasks.SessionLocal', return_value=db_session):
        result = cleanup_expired_links()
        assert "Cleaned up 1 expired links" in result

    db_session.expire_all()
    updated_link = db_session.query(Link).filter(Link.id == link_id).first()
    assert updated_link.is_active is False

def test_cleanup_unused_links(db_session, test_user):
    """Тест очистки неиспользуемых ссылок"""

    unused_link = Link(
        original_url="https://unused.com",
        short_code="unused",
        owner_id=test_user.id,
        last_clicked_at=datetime.utcnow() - timedelta(days=31),
        is_active=True
    )
    db_session.add(unused_link)
    db_session.commit()

    link_id = unused_link.id
    
    with patch('app.tasks.SessionLocal', return_value=db_session):
        result = cleanup_unused_links(30)
        assert "Cleaned up 1 unused links" in result

    db_session.expire_all()
    updated_link = db_session.query(Link).filter(Link.id == link_id).first()
    assert updated_link.is_active is False

def test_increment_click_count(db_session, test_link):
    """Тест увеличения счетчика кликов"""

    link_id = test_link.id
    initial_clicks = test_link.clicks
    
    with patch('app.tasks.SessionLocal', return_value=db_session):
        result = increment_click_count(link_id)
        assert f"Incremented clicks for link {link_id}" in result

    db_session.expire_all()
    updated_link = db_session.query(Link).filter(Link.id == link_id).first()
    
    assert updated_link.clicks == initial_clicks + 1
    assert updated_link.last_clicked_at is not None

def test_increment_click_count_nonexistent_link(db_session):
    """Тест увеличения счетчика для несуществующей ссылки"""
    with patch('app.tasks.SessionLocal', return_value=db_session):
        result = increment_click_count("nonexistent-id")
        assert "Incremented clicks for link nonexistent-id" in result

def test_cleanup_expired_links_no_expired(db_session):
    """Тест очистки когда нет истекших ссылок"""
    with patch('app.tasks.SessionLocal', return_value=db_session):
        result = cleanup_expired_links()
        assert "Cleaned up 0 expired links" in result

def test_cleanup_unused_links_no_unused(db_session, test_user):
    """Тест очистки когда нет неиспользуемых ссылок"""
    active_link = Link(
        original_url="https://active.com",
        short_code="active",
        owner_id=test_user.id,
        last_clicked_at=datetime.utcnow(),
        is_active=True
    )
    db_session.add(active_link)
    db_session.commit()
    
    with patch('app.tasks.SessionLocal', return_value=db_session):
        result = cleanup_unused_links(30)
        assert "Cleaned up 0 unused links" in result