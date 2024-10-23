import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from main import app
from src.services.auth import auth_serviсe
from src.entity.models import Base, User
from src.database.db import get_db

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create an async SQLAlchemy engine
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool, 
)

# Create a session maker for testing
TestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
)

# Sample user data for testing
test_user = {
    "username": "test_user",
    "email": "test_user@example.com",
    "password": "qwerty",
}


# Fixture to initialize database models and insert a test user
@pytest.fixture(scope="module", autouse=True)
def init_models_wraper():
    async def init_models():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)  # Drop existing tables
            await conn.run_sync(Base.metadata.create_all)  # Create tables
        async with TestingSessionLocal() as session:
            hash_password = auth_serviсe.get_password_hash(test_user["password"])
            current_user = User(
                username=test_user["username"],
                email=test_user["email"],
                password=hash_password,
                confirmed=True,
            )
            session.add(current_user)
            await session.commit()  # Commit the transaction

    asyncio.run(init_models())  # Run the initialization coroutine


# Fixture for the TestClient with overridden get_db dependency
@pytest.fixture(scope="module")
def client():
    async def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        except Exception as err:
            print(err)
            await session.rollback()
        finally:
            await session.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestClient(app)


# Fixture for creating an access token for testing
@pytest_asyncio.fixture()
async def get_token():
    token = await auth_serviсe.create_access_token(data={"sub": test_user["email"]})
    return token
