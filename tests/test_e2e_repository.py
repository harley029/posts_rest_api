from datetime import datetime, timedelta
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from fastapi import HTTPException
from fastapi_mail.errors import ConnectionErrors

from sqlalchemy.ext.asyncio import AsyncSession

from src.entity.models import User, Post, Comment
from src.schemas.user import UserSchema
from src.schemas.post import PostSchema, PostUpdateSchema
from src.schemas.comment import CommentModel, CommentUpdateSchema

from src.repository.users import (
    get_user_by_email,
    create_user,
    update_token,
    confirmed_email,
    update_password,
)
from src.repository.posts import (
    get_post,
    get_posts,
    get_censored_posts,
    get_post_comments,
    get_post_status,
    update_post,
    update_post_status,
    create_post,
    delete_post,
)
from src.repository.analitics import get_comments_daily_breakdown
from src.repository.comments import (
    get_comments,
    create_comment,
    get_censored_comments,
    get_comment,
    update_comment,
    delete_comment,
)
from src.services.ai import generate_reply
from src.services.email import send_email, send_password_reset_email


class TestRepositoryUser(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.user = User(
            id=1,
            username="test_user",
            email="test_user@example.com",
            password="qwerty",
            refresh_token="test_token",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            confirmed=True,
        )
        self.session = AsyncMock(spec=AsyncSession)

    async def test_get_user_by_email(self):
        email = "test_user@example.com"
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = self.user
        self.session.execute.return_value = mocked_result

        result = await get_user_by_email(email, self.session)

        self.assertEqual(result, self.user)

    async def test_get_user_by_email_not_found(self):
        email = "non_existent_user@example.com"
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_result

        result = await get_user_by_email(email, self.session)

        self.assertIsNone(result)

    async def test_create_user(self):
        body = UserSchema(
            username="new_user",
            email="new_user@example.com",
            password="password_1",
        )
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_result
        # Мокаем методы сессии
        self.session.add = AsyncMock()
        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()

        result = await create_user(body, self.session)

        self.assertIsInstance(result, User)
        self.assertEqual(result.username, body.username)
        self.assertEqual(result.email, body.email)

        self.session.add.assert_called_once()
        self.session.commit.assert_called_once()
        self.session.refresh.assert_called_once()

    async def test_create_existing_user(self):
        body = UserSchema(
            username="existing_user",
            email="existing_user@example.com",
            password="password_1",
        )
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = self.user
        self.session.execute.return_value = mocked_result

        with self.assertRaises(HTTPException) as exc:
            await create_user(body, self.session)

        self.assertEqual(exc.exception.status_code, 400)
        self.assertEqual(exc.exception.detail, "User is already exists")

        self.session.add.assert_not_called()
        self.session.commit.assert_not_called()

    async def test_update_token(self):
        new_token = "new_refresh_token"
       
        await update_token(self.user, new_token, self.session)
       
        self.assertEqual(self.user.refresh_token, new_token)
        self.session.commit.assert_called_once()

    async def test_confirmed_email(self):
        email = "test_user@example.com"
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = self.user
        self.session.execute.return_value = mocked_result
       
        await confirmed_email(email, self.session)
       
        self.assertTrue(self.user.confirmed)
        self.session.commit.assert_called_once()
        self.session.refresh.assert_called_once()

    async def test_update_password(self):
        new_password = "password"
        
        await update_password(self.user, new_password, self.session)
        
        self.assertEqual(self.user.password, new_password)
        self.session.commit.assert_called_once()
        self.session.refresh.assert_called_once()

    async def asyncTearDown(self):
        await self.session.close()


class TestRepositoryPost(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.user = User(
            id=1,
            username="test_user",
            email="test_user@example.com",
            password="qwerty",
            refresh_token="test_token",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            confirmed=True,
        )
        self.post = [
            Post(
                id=1,
                title="Test_title_1",
                content="test_post_1",
                status="published",
                user_id=1,
                censored=False,
                automatic_reply_enabled=True,
                reply_delay=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Post(
                id=2,
                title="Test_title_2",
                content="test_post_2",
                status="draft",
                user_id=1,
                censored=True,
                automatic_reply_enabled=True,
                reply_delay=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Post(
                id=3,
                title="Test_title_3",
                content="test_post_3",
                status="published",
                user_id=1,
                censored=True,
                automatic_reply_enabled=True,
                reply_delay=0,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]
        self.comment = [
            Comment(
                id=1,
                content="Test_comment_1",
                user_id=1,
                post_id=1,
                censored=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            Comment(
                id=2,
                content="Test_comment_2",
                user_id=1,
                post_id=2,
                censored=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]
        self.session = AsyncMock(spec=AsyncSession)

    async def test_get_posts(self):
        limit = 10
        offset = 0
        mocked_result = MagicMock()
        mocked_result.scalars.return_value.all.return_value = self.post
        self.session.execute.return_value = mocked_result
       
        result = await get_posts(1, 0, self.session)
       
        self.assertEqual(result, self.post)

    async def test_get_post(self):
        post_id = 1
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = self.post[0]
        self.session.execute.return_value = mocked_result
       
        result = await get_post(post_id, self.session)
       
        self.assertEqual(result, self.post[0])

    async def test_get_wrong_post(self):
        post_id = 4
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_result
       
        with self.assertRaises(HTTPException) as exc_info:
            await get_post(post_id, self.session)
       
        self.assertEqual(exc_info.exception.status_code, 404)
        self.assertEqual(exc_info.exception.detail, "Post has not been found")

    async def test_get_censored_posts(self):
        limit = 10
        offset = 0
        mocked_result = MagicMock()
        mocked_result.scalars.return_value.all.return_value = self.post[1:]
        self.session.execute.return_value = mocked_result
        
        result = await get_censored_posts(limit, offset, self.session)
        
        self.assertEqual(result, self.post[1:])

    async def test_update_post(self):
        post_id = 1
        censored = False
        body = PostUpdateSchema(
            title="Updated_title",
            content="Updated_content",
            status="published",
        )
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = self.post[0]
        self.session.execute.return_value = mocked_result
       
        result = await update_post(post_id, body, self.session, self.user, censored)
       
        self.assertIsInstance(result, Post)
        self.assertEqual(result.title, "Updated_title")
        self.assertEqual(result.content, "Updated_content")
        self.assertEqual(result.status, "published")
        self.session.commit.assert_called_once()

    async def test_delte_post(self):
        post_id = 1
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = self.post[0]
        self.session.execute.return_value = mocked_result
        
        result = await delete_post(post_id, self.session, self.user)
        
        self.session.delete.assert_called_once()
        self.session.commit.assert_called_once()
        self.assertIsInstance(result, Post)

    async def test_delte_wrong_post(self):
        post_id = 4
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_result
        
        result = await delete_post(post_id, self.session, self.user)
        
        self.session.delete.assert_not_called()
        self.session.commit.assert_not_called()
        self.assertIsNone(result)

    async def test_get_post_status(self):
        post_id = 1
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = "published"
        self.session.execute.return_value = mocked_result
        
        result = await get_post_status(post_id, self.session)
        
        self.assertEqual(result, self.post[0].status)

    async def test_get_wrong_post_status(self):
        post_id = 4
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_result
        
        result = await get_post_status(post_id, self.session)
        
        self.assertEqual(result, None)

    async def test_update_post_status(self):
        post_id = 1
        new_status = "draft"
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = self.post[0]
        self.session.execute.return_value = mocked_result
       
        result = await update_post_status(post_id, new_status, self.session, self.user)
       
        self.assertEqual(result.status, new_status)
        self.session.commit.assert_called_once()

    async def test_update_wrong_post_status(self):
        post_id = 4
        new_status = "draft"
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_result
       
        result = await update_post_status(post_id, new_status, self.session, self.user)
       
        self.assertEqual(result, None)

    async def test_create_post(self):
        title = "New_post_title"
        content = "New_post_content"
        status = "published"
        automatic_reply_enabled=True
        reply_delay=0
        body = PostSchema(
            title=title,
            content=content,
            status=status,
            automatic_reply_enabled=automatic_reply_enabled,
            reply_delay=reply_delay,
        )
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_result

        new_post = Post(
            id=3,
            title=title,
            content=content,
            status=status,
            user_id=1,
            censored=False,
            automatic_reply_enabled=True,
            reply_delay=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.session.add = AsyncMock()
        self.session.commit = AsyncMock() 
        self.session.refresh = AsyncMock() 

        result = await create_post(body, self.session, self.user)

        self.assertIsInstance(result, Post)
        self.assertEqual(result.title, new_post.title)
        self.assertEqual(result.content, new_post.content)
        self.assertEqual(result.status, new_post.status)
        self.assertEqual(result.censored, new_post.censored)
        self.assertEqual(result.automatic_reply_enabled, new_post.automatic_reply_enabled)
        self.assertEqual(result.reply_delay, new_post.reply_delay)
        self.session.add.assert_called_once_with(result)
        self.session.commit.assert_called_once()
        self.session.refresh.assert_called_once_with(result)

    async def test_create_existing_post(self):
        title = "Existing_post_title"
        content = "Existing_post_content"
        status = "published"
        automatic_reply_enabled = True
        reply_delay = 0
        body = PostSchema(
            title=title,
            content=content,
            status=status,
            automatic_reply_enabled=automatic_reply_enabled,
            reply_delay=reply_delay,
        )
        existing_post = Post(
            id=1,
            title=title,
            content=content,
            status=status,
            user_id=1,
            censored=False,
            automatic_reply_enabled=automatic_reply_enabled,
            reply_delay=reply_delay,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        # Существующий пост при проверке дубликатов
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = existing_post
        self.session.execute.return_value = mocked_result

        with self.assertRaises(HTTPException) as context:
            await create_post(body, self.session, self.user)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.detail, "Post is already exist")

        self.session.add.assert_not_called()
        self.session.commit.assert_not_called()
        self.session.refresh.assert_not_called()

    async def test_get_post_comments(self):
        post_id = 1
        mocked_result = MagicMock()
        mocked_result.scalars.return_value.all.return_value = self.comment[1:]
        self.session.execute.return_value = mocked_result
       
        result = await get_post_comments(post_id, self.session)
       
        self.assertEqual(result, self.comment[1:])

    async def test_get_post_without_comments(self):
        post_id = 3
        mocked_result = MagicMock()
        mocked_result.scalars.return_value.all.return_value = []
        self.session.execute.return_value = mocked_result
       
        result = await get_post_comments(post_id, self.session)
       
        self.assertEqual(result, [])

    async def test_create_censored_post(self):
        title = "New_post_title"
        content = "This post contains bad words"
        status = "published"
        automatic_reply_enabled = True
        reply_delay = 0
        body = PostSchema(
            title=title,
            content=content,
            status=status,
            automatic_reply_enabled=automatic_reply_enabled,
            reply_delay=reply_delay,
        )

        # Имитация того, что пост не существует
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_result

        # Мокаем функцию проверки на нецензурную лексику, чтобы она возвращала True
        result = await create_post(body, self.session, self.user, censored=True)

        self.assertIsInstance(result, Post)
        self.assertIsInstance(result, Post)
        self.assertEqual(result.title, title)
        self.assertEqual(result.content, content)
        self.assertEqual(result.status, status)
        self.assertEqual(result.censored, True)
        self.assertEqual(result.automatic_reply_enabled, automatic_reply_enabled)
        self.assertEqual(result.reply_delay, reply_delay)

        self.session.add.assert_called_once_with(result)
        self.session.commit.assert_called_once()
        self.session.refresh.assert_called_once_with(result)

    async def asyncTearDown(self):
        await self.session.close()


class TestRepositoryComments(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.user = User(
            id=1,
            username="test_user",
            email="test_user@example.com",
            password="qwerty",
            refresh_token="test_token",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            confirmed=True,
        )
        self.session = AsyncMock(spec=AsyncSession)
        self.comment_1 = Comment(
            id=1,
            content="Test_comment_1",
            user_id=1,
            post_id=1,
            censored=False,
            created_at=datetime.now() - timedelta(days=1),
            updated_at=datetime.now(),
        )
        self.comment_2 = Comment(
            id=2,
            content="Test_comment_2",
            user_id=1,
            post_id=1,
            censored=False,
            created_at=datetime.now() - timedelta(days=2),
            updated_at=datetime.now(),
        )

    async def test_get_comments_daily_breakdown(self):
        date_from = datetime.now() - timedelta(days=7)
        date_to = datetime.now()

        mocked_result = MagicMock()
        mocked_result.fetchall.return_value = [
            MagicMock(date=(datetime.now() - timedelta(days=1)).date(), comment_count=1),
            MagicMock(date=(datetime.now() - timedelta(days=2)).date(), comment_count=1),
        ]
        self.session.execute.return_value = mocked_result
        
        result = await get_comments_daily_breakdown(date_from, date_to, self.session, self.user)
        expected_result = {
            (datetime.now() - timedelta(days=1)).date(): 1,
            (datetime.now() - timedelta(days=2)).date(): 1,
        }
        
        self.assertEqual(result, expected_result)

    async def test_get_comments_daily_breakdown_empty(self):
        date_from = datetime.now() - timedelta(days=7)
        date_to = datetime.now()
        mocked_result = MagicMock()
        mocked_result.fetchall.return_value = []
        self.session.execute.return_value = mocked_result
        
        result = await get_comments_daily_breakdown(date_from, date_to, self.session, self.user)
        
        self.assertEqual(result, {})

    async def asyncTearDown(self):
        await self.session.close()


class TestRepositoryСomment(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.user = User(
            id=1,
            username="test_user",
            email="test_user@example.com",
            password="password_123",
        )
        self.comment = Comment(
            id=1, content="Test comment", user_id=self.user.id, censored=False
        )
        self.session = AsyncMock(spec=AsyncSession)

    async def test_get_comments(self):
        mocked_result = MagicMock()
        mocked_result.scalars().all.return_value = [self.comment]
        self.session.execute.return_value = mocked_result
        result = await get_comments(self.session)
        self.assertEqual(result, [self.comment])

    async def test_create_comment(self):
        body = CommentModel(content="New test comment", post_id=1)
        self.session.add = AsyncMock()
        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()

        result = await create_comment(body, self.session, self.user)
        self.assertIsInstance(result, Comment)
        self.assertEqual(result.content, body.content)
        self.assertEqual(result.user_id, self.user.id)
        self.assertEqual(result.post_id, body.post_id)

        self.session.add.assert_called_once()
        self.session.commit.assert_called_once()
        self.session.refresh.assert_called_once()

    async def test_create_censored_comment(self):
        body = CommentModel(content="Inappropriate comment", post_id=1)
        self.session.add = AsyncMock()
        self.session.commit = AsyncMock()
        self.session.refresh = AsyncMock()

        result = await create_comment(body, self.session, self.user, censored=True)
        self.assertTrue(result.censored)

    async def test_get_censored_comments(self):
        mocked_result = MagicMock()
        mocked_result.scalars().all.return_value = [self.comment]
        self.session.execute.return_value = mocked_result

        result = await get_censored_comments(10, 0, self.session, self.user)
        self.assertEqual(result, [self.comment])

    async def test_get_comment(self):
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = self.comment
        self.session.execute.return_value = mocked_result

        result = await get_comment(self.comment.id, self.session)
        self.assertEqual(result, self.comment)

    async def test_get_nonexistent_comment(self):
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_result

        result = await get_comment(999, self.session)
        self.assertIsNone(result)

    async def test_update_comment(self):
        body = CommentUpdateSchema(content="Updated content")
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = self.comment
        self.session.execute.return_value = mocked_result

        result = await update_comment(self.comment.id, body, self.session, self.user)
        self.assertEqual(result.content, "Updated content")

        self.session.commit.assert_called_once()
        self.session.refresh.assert_called_once_with(self.comment)

    async def test_update_nonexistent_comment(self):
        body = CommentUpdateSchema(content="Updated content")
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_result

        result = await update_comment(999, body, self.session, self.user)
        self.assertIsNone(result)

        self.session.commit.assert_not_called()

    async def test_delete_comment(self):
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = self.comment
        self.session.execute.return_value = mocked_result

        result = await delete_comment(self.comment.id, self.session, self.user)
        self.assertEqual(result, self.comment)

        self.session.delete.assert_called_once_with(self.comment)
        self.session.commit.assert_called_once()

    async def test_delete_nonexistent_comment(self):
        mocked_result = MagicMock()
        mocked_result.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_result

        result = await delete_comment(999, self.session, self.user)
        self.assertIsNone(result)

        self.session.delete.assert_not_called()
        self.session.commit.assert_not_called()

    async def asyncTearDown(self):
        await self.session.close()


class Test_AI_Reply(unittest.IsolatedAsyncioTestCase):

    @pytest.mark.asyncio
    @patch("src.services.ai.genai.GenerativeModel")
    async def test_generate_reply_success(self, mock_model):
        mock_generate_content = AsyncMock()
        mock_generate_content.return_value.text = "Это пример ответа на комментарий."
        mock_model.return_value.generate_content = mock_generate_content
        post_content = "Это тестовый пост"
        comment_content = "Это тестовый комментарий"

        result = await generate_reply(post_content, comment_content)

        assert result == "Это пример ответа на комментарий."
        mock_model.assert_called_once_with("gemini-1.5-flash")
        mock_generate_content.assert_called_once_with(
            f"""
    Пост: "{post_content}"
    Комментарий: "{comment_content}"
    Як автор посту, напиши відповідь на цей коментар, який буде релевантним та корисним.
    """.strip()
        )

    @pytest.mark.asyncio
    @patch("src.services.ai.genai.GenerativeModel")
    async def test_generate_reply_error(self, mock_model):
        mock_model.side_effect = Exception("API error")
        post_content = "Це тестовий пост"
        comment_content = "Це тестовий коментар"

        result = await generate_reply(post_content, comment_content)

        assert result == "Дякую за Ваш коментар!"
        mock_model.assert_called_once_with("gemini-1.5-flash")


class TestEmailService(unittest.IsolatedAsyncioTestCase):

    @pytest.mark.asyncio
    @patch("src.services.auth.auth_serviсe.create_email_token")
    @patch("src.services.email.FastMail")
    async def test_send_email_success(self, mock_fastmail, mock_create_email_token):
        mock_create_email_token.return_value = "test_token"
        mock_fastmail_instance = AsyncMock()
        mock_fastmail.return_value = mock_fastmail_instance
        email = "test@example.com"
        username = "testuser"
        host = "http://testserver.com"

        await send_email(email, username, host)
        mock_create_email_token.assert_called_once_with({"sub": email})
        mock_fastmail_instance.send_message.assert_awaited_once()
        args, kwargs = mock_fastmail_instance.send_message.call_args
        message = args[0]

        self.assertEqual(message.subject, "Confirm your email ")
        self.assertEqual(message.recipients, [email])
        self.assertEqual(
            message.template_body,
            {
                "host": host,
                "username": username,
                "token": "test_token",
            },
        )
        self.assertEqual(message.subtype.value, "html")
        self.assertEqual(kwargs["template_name"], "email_verification.html")

    @pytest.mark.asyncio
    @patch("src.services.auth.auth_serviсe.create_email_token")
    @patch("src.services.email.FastMail")
    async def test_send_email_connection_error(
        self, mock_fastmail, mock_create_email_token
    ):
        mock_create_email_token.return_value = "test_token"
        mock_fastmail_instance = AsyncMock()
        mock_fastmail_instance.send_message.side_effect = ConnectionErrors(
            "Connection error"
        )
        mock_fastmail.return_value = mock_fastmail_instance
        email = "test@example.com"
        username = "testuser"
        host = "http://testserver.com"

        with patch("builtins.print") as mock_print:
            await send_email(email, username, host)
            mock_print.assert_called_once_with("Connection error")

    @pytest.mark.asyncio
    @patch("src.services.auth.auth_serviсe.create_email_token")
    @patch("src.services.email.FastMail")
    async def test_send_password_reset_email_success(
        self, mock_fastmail, mock_create_email_token
    ):
        mock_create_email_token.return_value = "test_token"
        mock_fastmail_instance = AsyncMock()
        mock_fastmail.return_value = mock_fastmail_instance

        email = "test@example.com"
        username = "testuser"
        host = "http://testserver.com"

        await send_password_reset_email(email, username, host)

        mock_create_email_token.assert_called_once_with({"sub": email})
        # Перевіряємо, що send_message викликано з правильними аргументами
        mock_fastmail_instance.send_message.assert_awaited_once()
        args, kwargs = mock_fastmail_instance.send_message.call_args
        # Перевіряємо властивості повідомлення
        message = args[0]
        self.assertEqual(message.subject, "Password reset ")
        self.assertEqual(message.recipients, [email])
        self.assertEqual(
            message.template_body,
            {
                "host": host,
                "username": username,
                "token": "test_token",
            },
        )
        self.assertEqual(message.subtype.value, "html")
        # Перевіряємо, що використано правильний шаблон
        self.assertEqual(kwargs["template_name"], "password_reset_mail.html")

    @pytest.mark.asyncio
    @patch("src.services.auth.auth_serviсe.create_email_token")
    @patch("src.services.email.FastMail")
    async def test_send_password_reset_email_connection_error(
        self, mock_fastmail, mock_create_email_token
    ):
        mock_create_email_token.return_value = "test_token"
        mock_fastmail_instance = AsyncMock()
        # Raise ConnectionErrors instead of Exception
        mock_fastmail_instance.send_message.side_effect = ConnectionErrors(
            "Connection error"
        )
        mock_fastmail.return_value = mock_fastmail_instance
        email = "test@example.com"
        username = "testuser"
        host = "http://testserver.com"

        with patch("builtins.print") as mock_print:
            await send_password_reset_email(email, username, host)
            mock_print.assert_called_once_with("Connection error")
