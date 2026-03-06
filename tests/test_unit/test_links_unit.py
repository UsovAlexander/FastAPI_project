import pytest
import string
from unittest.mock import patch, Mock
from app.routers.links import generate_short_code

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