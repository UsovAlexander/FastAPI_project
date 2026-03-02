## API-сервис сокращения ссылок

1.  **Клонируйте репозиторий:**
    ```bash
    git clone https://github.com/UsovAlexander/FastAPI_project.git
    cd FastAPI_project
    ```

2.  **Создайте виртуальное окружение и установите зависимости:**
    ```bash
    python3.12 -m venv venv_fastapi_project

    source ./venv_fastapi_project/bin/activate
    
    pip install -r requirements.txt
    ```

3. **Работа с контейнером:**

 - Cоберите с очисткой кэша
    ```bash
    docker-compose build --no-cache
    ```

 - Запустите
    ```bash
    docker-compose up -d
    ```

 - Проверьте логи
    ```bash
    docker-compose logs -f web
    ```
 - Остановите контейнеры
    ```bash
    docker-compose down
    ```

4. **Работа с тестами:**
 - Запуск pytest
    ```bash
    coverage run -m pytest tests/ -v
    ```
 - Отчет
    ```bash
    coverage report -m
    ```
 - Отчет в HTML
    ```bash
    coverage html && open htmlcov/index.html
    ```

 - Запуск locust для тестов под нагрузкой
   ```bash
   locust -f tests/locustfile.py --host=http://localhost:8000
   ```