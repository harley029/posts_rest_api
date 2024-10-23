from pathlib import Path

from fastapi.security import OAuth2PasswordBearer
from fastapi_mail import ConnectionConfig
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    pg_db: str
    pg_user: str
    pg_password: str
    pg_port: int
    pg_domain: str
    db_url: str
    secret_key_jwt: str
    algorithm: str
    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: int
    mail_server: str
    redis_url: str
    redis_port: int
    api_key: str
    respective_api_url:str
    celery_broker_url:str
    celery_backend:str
    google_reply_api_key:str

    model_config = ConfigDict(
        extra="ignore", env_file=".env", env_file_encoding="utf-8"
    )

settings = Settings()

# ключ для аутентифікації користувачів
SECRET_KEY = settings.secret_key_jwt
ALGORITHM = settings.algorithm

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_FROM_NAME="Harley's posts email System :)",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).parent.parent / "services/templates",
)

# ключ для моделі модерації постів та коментарів
API_KEY = settings.api_key
PERSPECTIVE_API_URL = settings.respective_api_url

# ключ для моделі відповіді на коментарі
GOOGLE_REPLY_API_KEY = settings.google_reply_api_key

# налаштування для Celery
CELERY_BROKER_URL = settings.celery_broker_url
CELERY_BACKEND = settings.celery_backend
