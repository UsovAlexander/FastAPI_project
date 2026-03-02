import pytest
import string
from unittest.mock import patch, Mock, MagicMock
from app.routers.links import generate_short_code, increment_click_count


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

def test_increment_click_count_task():
    """Тест задачи инкремента кликов"""
    with patch('app.routers.links.increment_click_count.delay') as mock_delay:
        increment_click_count.delay("test_link_id")
        mock_delay.assert_called_once_with("test_link_id")