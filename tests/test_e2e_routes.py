from unittest.mock import AsyncMock, patch
from typing import List

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import select

from src.entity.models import User, Comment
from tests.conftest import TestingSessionLocal
from src.services.auth import auth_serviсe
from src.repository import users as repositories_users
from src.schemas.comment import CommentResponseSchema
from src.schemas.user import UserResponseSchema


user_data = {
    "username": "testuser",
    "email": "testuser@mail.com",
    "password": "qwerty",
}

@pytest.fixture
def mock_comments():
    return [
    CommentResponseSchema(
        id=1,
        content="Test comment 1",
        user=UserResponseSchema(
            id=1, username="testuser", email="testuser@example.com"
        ),
        censored=False,
    ),
    CommentResponseSchema(
        id=2,
        content="Test comment 2",
        user=UserResponseSchema(
            id=2, username="anotheruser", email="another@example.com"
        ),
        censored=False,
    ),
]


@pytest.fixture
def mock_user():
    return User(
        id=1,
        username="testuser",
        email="testuser@mail.com",
        password="qwerty",
        confirmed=True,
        refresh_token="mock_refresh_token",
    )


def test_signup(client):
    with patch("fastapi.Request.client", create=True) as mock_client:
        mock_client.host = "127.0.0.1"
        response = client.post("/api/auth/signup", json=user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert "password" not in data


@pytest.mark.asyncio
async def test_successful_login(client: TestClient):
    with patch("fastapi.Request.client", create=True) as mock_client:
        mock_client.host = "127.0.0.1"
        mock_user = User(
            email="testuser@mail.com",
            username="testuser",
            password=auth_serviсe.get_password_hash("qwerty"),
            confirmed=True,
        )
        repositories_users.get_user_by_email = AsyncMock(return_value=mock_user)
        repositories_users.update_token = AsyncMock()
        # Mocking authentication service functions
        auth_serviсe.verify_password = AsyncMock(return_value=True)
        auth_serviсe.create_access_token = AsyncMock(return_value="access_token")
        auth_serviсe.create_refresh_token = AsyncMock(return_value="refresh_token")
        # Make the request
        response = client.post(
            "/api/auth/login",
            data={"username": "testuser@mail.com", "password": "qwerty"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_token(client: TestClient, mock_user: User):
    with patch(
        "src.services.auth.auth_serviсe.decode_refresh_token",
        return_value=mock_user.email,
    ):
        with patch(
            "src.repository.users.get_user_by_email", AsyncMock(return_value=mock_user)
        ):
            response = client.get(
                "/api/auth/refresh_token",
                headers={"Authorization": "Bearer mock_refresh_token"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data


@pytest.mark.asyncio
async def test_get_comments(client: TestClient, mock_comments: List[Comment]):
    with patch(
        "src.repository.comments.get_comments", AsyncMock(return_value=mock_comments)
    ):
        response = client.get("/api/comments")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(mock_comments)
        assert data[0]["content"] == mock_comments[0].content
