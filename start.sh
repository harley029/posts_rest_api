# Start the Celery worker in the background
celery -A src.celery.celery_app.celery_app worker --loglevel=info &

# Start the Uvicorn server in the foreground
uvicorn main:app --host 0.0.0.0 --port 8000 --reload