from datetime import datetime, timedelta, timezone
from typing import Optional

from redis.asyncio.client import Redis
import pickle

from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from src.entity.models import User
from src.database.db import get_db, get_redis_client
from src.repository import users as repositories_users
from src.config.config import SECRET_KEY, ALGORITHM, oauth2_scheme


class Auth:

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password, hashed_password):
        """
        Verifies if the plain password matches the hashed password.

        Args:
            plain_password (str): The plain text password to be verified.
            hashed_password (str): The hashed password to be compared with the plain text password.

        Returns:
            bool: Returns True if the plain password matches the hashed password, otherwise False.

        Raises:
            Exception: If the password context is not initialized.
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        """
        Hashes the given password using the bcrypt algorithm.

        Args:
            password (str): The plain text password to be hashed.

        Returns:
            str: The hashed password as a string.

        Raises:
            Exception: If the password context is not initialized.
        """
        return self.pwd_context.hash(password)

    async def create_access_token(
        self, data: dict, expires_delta: Optional[float] = None
    ):
        """
        Generates an access token for the user.

        Args:
            data (dict): A dictionary containing user-specific data.
            expires_delta (Optional[float], optional): The time in seconds that the token should be valid for. Defaults to 15 minutes.

        Returns:
            str: The generated access token.

        Raises:
            Exception: If the token generation process fails.

        Note:
            The token is generated using the JWT library with the provided SECRET_KEY and ALGORITHM.
        """
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + timedelta(seconds=expires_delta)
        else:
            expire = now + timedelta(minutes=15)
        to_encode.update({"iat": now, "exp": expire, "scope": "access_token"})
        encoded_access_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_access_token

    async def create_refresh_token(
        self, data: dict, expires_delta: Optional[float] = None
    ):
        """
        Generates a refresh token for the user.

        Args:
            data (dict): A dictionary containing user-specific data.
            expires_delta (Optional[float], optional): The time in seconds that the token should be valid for. Defaults to 7 days.

        Returns:
            str: The generated refresh token.

        Raises:
            Exception: If the token generation process fails.

        Note:
            The token is generated using the JWT library with the provided SECRET_KEY and ALGORITHM.
        """
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + timedelta(seconds=expires_delta)
        else:
            expire = now + timedelta(days=7)
        to_encode.update({"iat": now, "exp": expire, "scope": "refresh_token"})
        encoded_refresh_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_refresh_token

    async def decode_refresh_token(self, refresh_token: str):
        """
        Decodes a refresh token to retrieve the user's email.

        Args:
            refresh_token (str): The refresh token to be decoded.

        Returns:
            str: The user's email if the token is valid and has a valid scope.

        Raises:
            HTTPException: If the token cannot be decoded or has an invalid scope.

        Note:
            The token is decoded using the JWT library with the provided SECRET_KEY and ALGORITHM.
        """
        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload["scope"] == "refresh_token":
                email = payload["sub"]
                return email
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid scope for token",
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

    async def get_current_user(
        self,
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
        redis_client: Redis = Depends(get_redis_client),
    ):
        """
        Retrieves the current user from the token provided.

        Args:
            token (str): The token to be decoded and validated.
            db (AsyncSession, optional): The database session to be used for retrieving user data. Defaults to Depends(get_db).
            redis_client (Redis, optional): The Redis client to be used for caching user data. Defaults to Depends(get_redis_client).

        Returns:
            User: The current user object if the token is valid and has a valid scope.

        Raises:
            HTTPException: If the token cannot be decoded or has an invalid scope.

        Note:
            The token is decoded using the JWT library with the provided SECRET_KEY and ALGORITHM.
            If the user data is found in Redis, it is returned directly. Otherwise, the user data is retrieved from the database and cached in Redis before being returned.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        # Decode JWT token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload["scope"] != "access_token":
                raise credentials_exception
            email = payload.get("sub")
            if email is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception

        # Retrieve user from cache or database
        try:
            redis_key = f"user_data:{email}"
            user_data = await redis_client.get(redis_key)
            if user_data:
                print("User is retrieved from Redis cache")
                user_dict = pickle.loads(user_data)
                user = User(**user_dict)
            else:
                print("User is retrieved from Database")
                user = await repositories_users.get_user_by_email(email, db)
                if user is None:
                    raise credentials_exception
                # Serialize user data to JSON
                user_dict = {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                }
                await redis_client.set(redis_key, pickle.dumps(user_dict), ex=60 * 15)
        except Exception as e:
            print(f"Error in get_current_user: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

        return user

    def create_email_token(self, data: dict):
        """
        Generates an email token for the user.

        Args:
            data (dict): A dictionary containing user-specific data.

        Returns:
            str: The generated email token.

        Note:
            The token is generated using the JWT library with the provided SECRET_KEY and ALGORITHM.
            The token has a validity of 1 day.
        """
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=1)
        to_encode.update({"iat": now, "exp": expire})
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return token

    async def get_email_from_token(self, token: str):
        """
        Decodes a token to retrieve the user's email.

        Args:
            token (str): The token to be decoded.

        Returns:
            str: The user's email if the token is valid.

        Raises:
            HTTPException: If the token cannot be decoded or has an invalid scope.

        Note:
            The token is decoded using the JWT library with the provided SECRET_KEY and ALGORITHM.
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email = payload["sub"]
            return email
        except JWTError as e:
            print(e)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid token for email verification",
            )


auth_serviсe = Auth()
