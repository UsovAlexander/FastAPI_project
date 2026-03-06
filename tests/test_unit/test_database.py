import pytest
import os
from unittest.mock import patch, Mock, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from app.database import (
    get_database_url, init_db_engine, get_db, 
    is_db_connected, engine, SessionLocal
)

def test_get_database_url_success():
    """Тест успешного получения DATABASE_URL"""
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test:test@localhost/test"}):
        url = get_database_url()
        assert url == "postgresql://test:test@localhost/test"

def test_get_database_url_not_found():
    """Тест когда DATABASE_URL не найден"""
    with patch.dict(os.environ, {}, clear=True):
        url = get_database_url()
        assert url is None

def test_init_db_engine_success():
    """Тест успешной инициализации engine"""
    mock_engine = MagicMock()
    mock_connection = MagicMock()
    mock_connection.execute.return_value = None
    mock_engine.connect.return_value.__enter__.return_value = mock_connection
    
    with patch('app.database.get_database_url', return_value="postgresql://test:test@localhost/test"), \
         patch('app.database.create_engine', return_value=mock_engine) as mock_create_engine, \
         patch('app.database.Base.metadata.create_all') as mock_create_all:
        
        result = init_db_engine(retries=1, delay=0)
        assert result is not None
        mock_create_engine.assert_called_once()
        mock_create_all.assert_called_once()

def test_init_db_engine_no_url():
    """Тест инициализации без URL"""
    with patch('app.database.get_database_url', return_value=None):
        result = init_db_engine(retries=1, delay=0)
        assert result is None

def test_init_db_engine_connection_error():
    """Тест ошибки подключения"""
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = SQLAlchemyError("Connection error")
    
    with patch('app.database.get_database_url', return_value="postgresql://test:test@localhost/test"), \
         patch('app.database.create_engine', return_value=mock_engine):
        
        result = init_db_engine(retries=1, delay=0)
        assert result is None

def test_init_db_engine_with_render_url():
    """Тест инициализации с Render.com URL"""
    mock_engine = MagicMock()
    mock_connection = MagicMock()
    mock_connection.execute.return_value = None
    mock_engine.connect.return_value.__enter__.return_value = mock_connection
    
    with patch('app.database.get_database_url', return_value="postgresql://test:test@render.com/test"), \
         patch('app.database.create_engine', return_value=mock_engine) as mock_create_engine, \
         patch('app.database.Base.metadata.create_all'):
        
        result = init_db_engine(retries=1, delay=0)
        assert result is not None

        args, kwargs = mock_create_engine.call_args
        assert kwargs.get('connect_args') == {"sslmode": "require"}

def test_get_db_with_engine():
    """Тест get_db когда engine инициализирован"""
    from app.database import SessionLocal as original_session
    
    mock_session = MagicMock()
    
    with patch('app.database.SessionLocal', return_value=mock_session):
        db_gen = get_db()
        db = next(db_gen)
        assert db is not None
        
        with pytest.raises(StopIteration):
            next(db_gen)
        
        mock_session.close.assert_called_once()

def test_get_db_without_engine():
    """Тест get_db когда engine не инициализирован"""
    import app.database
    original_engine = app.database.engine
    original_session = app.database.SessionLocal
    
    app.database.engine = None
    app.database.SessionLocal = None
    
    with patch('app.database.init_db_engine') as mock_init:
        mock_init.return_value = None
        
        db_gen = get_db()
        db = next(db_gen)
        
        assert hasattr(db, 'query')
        assert hasattr(db, 'add')
        assert hasattr(db, 'commit')
        assert hasattr(db, 'close')
    
    app.database.engine = original_engine
    app.database.SessionLocal = original_session

def test_is_db_connected_success():
    """Тест успешной проверки подключения"""
    mock_engine = MagicMock()
    mock_connection = MagicMock()
    mock_connection.execute.return_value = None
    mock_engine.connect.return_value.__enter__.return_value = mock_connection
    
    import app.database
    original_engine = app.database.engine
    app.database.engine = mock_engine
    
    assert is_db_connected() is True
    
    app.database.engine = original_engine

def test_is_db_connected_no_engine():
    """Тест проверки подключения без engine"""
    import app.database
    original_engine = app.database.engine
    app.database.engine = None
    
    assert is_db_connected() is False
    
    app.database.engine = original_engine

def test_is_db_connected_error():
    """Тест ошибки при проверке подключения"""
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("Connection error")
    
    import app.database
    original_engine = app.database.engine
    app.database.engine = mock_engine
    
    assert is_db_connected() is False
    
    app.database.engine = original_engine