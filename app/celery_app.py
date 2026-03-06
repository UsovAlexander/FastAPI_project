from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

# Celery может стартовать до того, как переменные окружения будут полностью готовы
# Поэтому проверяем REDIS_URL при первом использовании, а не сразу
celery_app = Celery(
    "url_shortener",
    include=["app.tasks"]
)

# Настраиваем конфигурацию через метод, который будет вызван при старте воркера
def configure_celery(app):
    REDIS_URL = os.getenv("REDIS_URL")
    if not REDIS_URL:
        raise ValueError("REDIS_URL environment variable is not set")
    
    app.conf.update(
        broker_url=REDIS_URL,
        result_backend=REDIS_URL,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,
        result_expires=3600,
        broker_connection_retry_on_startup=True,
    )

# Вызываем конфигурацию при импорте (но это все еще может быть рано для Render)
# Лучше настроить это в самом воркере