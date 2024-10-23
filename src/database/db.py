from fastapi import HTTPException  

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import redis.asyncio as aioredis

from src.config.config import settings

DB_URL = settings.db_url
REDIS_URL = settings.redis_url  # для запуска из Докера (см файл main.py)
SYNC_DB_URL = f"postgresql://{settings.pg_user}:{settings.pg_password}@{settings.pg_domain}:{settings.pg_port}/{settings.pg_db}"


engine = create_async_engine(DB_URL)
local_session = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_db():
    """
    Asynchronously creates a database session using SQLAlchemy's async_sessionmaker.

    Parameters:
    None

    Returns:
    async_generator: An asynchronous generator yielding a SQLAlchemy session.

    Raises:
    HTTPException: If a SQLAlchemyError occurs during session creation, a 500 error is raised.
    """
    try:
        async with local_session() as session:
            yield session
    except SQLAlchemyError as e:
        print(f"Database session creation failed: {e}")
        raise HTTPException(status_code=500, detail="Database session creation failed")


async def get_redis_client():
    """
    Asynchronously creates a Redis client using aioredis.

    Parameters:
    None

    Returns:
    aioredis.Redis: An asynchronous Redis client.

    Raises:
    HTTPException: If a RedisError occurs during client creation, a 500 error is raised.
    """
    redis_client = aioredis.from_url(REDIS_URL)
    try:
        yield redis_client
    finally:
        try:
            await redis_client.close()
        except Exception as e:
            print(f"Error closing Redis client: {e}")
