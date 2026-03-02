import pytest
from app.routers.links import generate_short_code
import string
from app.routers.links import increment_click_count
from datetime import datetime, timedelta
from app.models import Link

def test_generate_short_code_default_length():
    """Тест генерации короткого кода стандартной длины"""
    code = generate_short_code()
    assert len(code) == 6
    assert all(c in string.ascii_letters + string.digits for c in code)

def test_generate_short_code_custom_length():
    """Тест генерации короткого кода с произвольной длиной"""
    code = generate_short_code(10)
    assert len(code) == 10
    assert all(c in string.ascii_letters + string.digits for c in code)

def test_generate_short_code_uniqueness():
    """Тест уникальности генерируемых кодов"""
    codes = [generate_short_code() for _ in range(100)]
    assert len(codes) == len(set(codes))

@pytest.mark.asyncio
async def test_increment_click_count_task(mock_celery_task):
    """Тест задачи инкремента кликов"""
    
    increment_click_count.delay("test_link_id")
    mock_celery_task.delay.assert_called_once_with("test_link_id")

def test_link_expiration_check(db_session, test_user):
    """Тест проверки истечения срока ссылки"""
    
    expired_link = Link(
        original_url="https://expired.com",
        short_code="expired",
        owner_id=test_user.id,
        expires_at=datetime.utcnow() - timedelta(days=1),
        is_active=True
    )
    db_session.add(expired_link)
    db_session.commit()
    
    assert expired_link.expires_at < datetime.utcnow()
    assert expired_link.is_active is True