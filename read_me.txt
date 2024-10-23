1. Миграции.
1.1 Ініціалізація міграцій
    alembic init migrations

Alembic не підтримує асинхронний режим, тому потрібно використовувати синхронний механізм для міграцій.
- в файлі db.py створити синхронний URL
    SYNC_DB_URL = f"postgresql://{settings.pg_user}:{settings.pg_password}@{settings.pg_domain}:{settings.pg_port}/{settings.pg_db}"
- изменения в файле migrations/env.py
    from src.entity.models import Base
    from src.database.db import SYNC_DB_URL

    target_metadata = Base.metadata
    config.set_main_option("sqlalchemy.url", SYNC_DB_URL)
- зміни в файлі alembic.ini (додати)
    sqlalchemy.url = postgresql://postgres:8lyrMibko@localhost:5432/myposts

1.2. Створення міграції
    alembic revision --autogenerate -m 'Init'
- зміни в файлі міграції    
    перенести id на початок таблиці (створюється в середині)

1.3. Проведення міграції
    alembic upgrade head

2. установка Pydantic e-mail validator 
    pipenv install 'pydantic[email]'

3. Запуск Celery
    celery -A src.celery.celery_app.celery_app worker --loglevel=info

4. Запуск тестів
    PYTHONPATH=. pytest -v

5. Звіт щодо покриття тестами
    - встановити pytest-coc
    PYTHONPATH=. pytest --cov ./src --cov-report html tests/