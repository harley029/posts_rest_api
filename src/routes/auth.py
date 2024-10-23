from fastapi.responses import JSONResponse
from redis.asyncio.client import Redis

from fastapi import (
    APIRouter,
    Form,
    HTTPException,
    Depends,
    Security,
    status,
    BackgroundTasks,
    Request,
)

from fastapi.templating import Jinja2Templates

from fastapi.security import (
    HTTPAuthorizationCredentials,
    OAuth2PasswordRequestForm,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.email import send_email, send_password_reset_email
from src.entity.models import User
from src.database.db import get_db, get_redis_client
from src.repository import users as repositories_users
from src.schemas.user import RequestEmail, UserSchema, TokenSchema, UserResponseSchema
from src.services.auth import auth_serviсe
from src.config.config import conf


router = APIRouter(prefix="/auth", tags=["auth"])

get_refresh_token = HTTPBearer()

# Ініціалізація Jinja2Templates з вказівкою на папку з шаблонами
templates = Jinja2Templates(directory=conf.TEMPLATE_FOLDER)


@router.post(
    "/signup", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED
)
async def signup(
    body: UserSchema,
    bt: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Sign up a new user.

    Parameters:
    - body (UserSchema): The user data to be created.
    - bt (BackgroundTasks): A task manager for asynchronous tasks.
    - request (Request): The HTTP request object.
    - db (AsyncSession): The database session.

    Returns:
    - UserResponseSchema: The newly created user object.

    Raises:
    - HTTPException: If the user already exists.
    """
    exist_user = await repositories_users.get_user_by_email(body.email, db)
    if exist_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Account already exists"
        )
    body.password = auth_serviсe.get_password_hash(body.password)
    new_user = await repositories_users.create_user(body, db)
    bt.add_task(send_email, new_user.email, new_user.username, str(request.base_url))
    return new_user


@router.post("/login", response_model=TokenSchema)
async def login(
    body: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Logs in a user and returns a JWT token.

    Parameters:
    - body (OAuth2PasswordRequestForm): The user credentials.
    - db (AsyncSession): The database session.

    Returns:
    - TokenSchema: A dictionary containing the access token, refresh token, and token type.

    Raises:
    - HTTPException: If the user does not exist, if the user is not confirmed, or if the password is incorrect.
    """
    user = await repositories_users.get_user_by_email(body.username, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )  # Invalid email
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )  # Not confirmed
    if not auth_serviсe.verify_password(body.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )  # Invalid password
    # Generate JWT
    access_token = await auth_serviсe.create_access_token(data={"sub": user.email})
    refresh_token = await auth_serviсe.create_refresh_token(data={"sub": user.email})
    await repositories_users.update_token(user, refresh_token, db)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.get("/refresh_token", response_model=TokenSchema)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Security(get_refresh_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh the user's access token.

    Parameters:
    - credentials (HTTPAuthorizationCredentials): The HTTP Authorization header containing the refresh token.
    - db (AsyncSession): The database session.

    Returns:
    - TokenSchema: A dictionary containing the new access token, refresh token, and token type.

    Raises:
    - HTTPException: If the refresh token is invalid or expired.
    """
    token = credentials.credentials
    email = await auth_serviсe.decode_refresh_token(token)
    user = await repositories_users.get_user_by_email(email, db)
    if user.refresh_token != token:
        await repositories_users.update_token(user=user, refresh_token=None, db=db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    access_token = await auth_serviсe.create_access_token(data={"sub": email})
    refresh_token = await auth_serviсe.create_refresh_token(data={"sub": email})
    await repositories_users.update_token(user, refresh_token, db)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.get("/confirmed_email/{token}")
async def confirmed_email(token: str, db: AsyncSession = Depends(get_db)):
    """
    Confirm the user's email address.

    Parameters:
    - token (str): The token sent to the user's email address for confirmation.
    - db (AsyncSession): The database session.

    Returns:
    - dict: A dictionary containing a message indicating whether the email address has been confirmed.

    Raises:
    - HTTPException: If the token is invalid or expired.
    """
    email = await auth_serviсe.get_email_from_token(token)
    user = await repositories_users.get_user_by_email(email, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    await repositories_users.confirmed_email(email, db)
    return {"message": "Email confirmed"}


@router.post("/request_email")
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a confirmation email for the user's email address.

    Parameters:
    - body (RequestEmail): A dictionary containing the user's email address.
    - background_tasks (BackgroundTasks): A task manager for asynchronous tasks.
    - request (Request): The HTTP request object.
    - db (AsyncSession): The database session.

    Returns:
    - dict: A dictionary containing a message indicating whether the email address has been confirmed.

    Raises:
    - HTTPException: If the user already has a confirmed email address.
    """
    user = await repositories_users.get_user_by_email(body.email, db)
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    if user:
        background_tasks.add_task(
            send_email, user.email, user.username, str(request.base_url)
        )
    return {"message": "Check your email for confirmation."}


@router.post("/request_password_reset")
async def request_password_reset(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset email for the user's email address.

    Parameters:
    - body (RequestEmail): A dictionary containing the user's email address.
    - background_tasks (BackgroundTasks): A task manager for asynchronous tasks.
    - request (Request): The HTTP request object.
    - db (AsyncSession): The database session.

    Returns:
    - dict: A dictionary containing a message indicating whether the email address has been confirmed.

    Raises:
    - HTTPException: If the user already has a confirmed email address.
    """
    user = await repositories_users.get_user_by_email(body.email, db)
    if user:
        background_tasks.add_task(
            send_password_reset_email, user.email, user.username, str(request.base_url)
        )
        return {"message": "Check your email to reset password."}
    else:
        return {"message": "User not found."}


@router.get("/reset_password/{token}")
async def confirmed_reset_password_email(
    token: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the reset password form for the user with the given token.

    Parameters:
    - token (str): The token sent to the user's email address for resetting the password.
    - request (Request): The HTTP request object.
    - db (AsyncSession): The database session.

    Returns:
    - TemplateResponse: A Flask template response containing the reset password form.

    Raises:
    - HTTPException: If the token is invalid or expired.
    """
    email = await auth_serviсe.get_email_from_token(token)
    user = await repositories_users.get_user_by_email(email, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification error"
        )
    return templates.TemplateResponse(
        "reset_password_form.html",
        {"request": request, "token": token},
    )


@router.post("/reset-password/")
async def reset_password(
    token: str = Form(...),
    new_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Reset the user's password using a token sent to their email address.

    Parameters:
    - token (str): The token sent to the user's email address for resetting the password.
    - new_password (str): The new password to be set for the user.
    - db (AsyncSession): The database session.

    Returns:
    - JSONResponse: A JSON response containing a message indicating the success of the password reset.

    Raises:
    - HTTPException: If the token is invalid or expired, or if the user is not found.
    """
    email = await auth_serviсe.get_email_from_token(token)
    user = await repositories_users.get_user_by_email(email, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_hashed_password = auth_serviсe.get_password_hash(new_password)
    await repositories_users.update_password(user, new_hashed_password, db)
    return JSONResponse(
        content={"message": "Password reset successful"}, status_code=200
    )


@router.post("/cash/set")
async def set_cash(
    key: str,
    value: str,
    redis_client: Redis = Depends(get_redis_client),
    user: User = Depends(auth_serviсe.get_current_user),
):
    """
    Sets a key-value pair in the Redis cache.

    Parameters:
    - key (str): The key to be set in the cache.
    - value (str): The value to be associated with the key in the cache.
    - redis_client (Redis): The Redis client used to interact with the cache.
    - user (User): The authenticated user making the request.

    Returns:
    - None: This method does not return a value.

    Raises:
    - HTTPException: If the user is not authenticated.
    """
    await redis_client.set(key, value)


@router.get("/cash/get/{key}")
async def get_cash(
    key: str,
    redis_client: Redis = Depends(get_redis_client),
    user: User = Depends(auth_serviсe.get_current_user),
):
    """
    Retrieves the value associated with the given key from the Redis cache.

    Parameters:
    - key (str): The key to be retrieved from the cache.
    - redis_client (Redis): The Redis client used to interact with the cache.
    - user (User): The authenticated user making the request.

    Returns:
    - dict: A dictionary containing the key and its associated value in the cache.

    Raises:
    - HTTPException: If the user is not authenticated.
    """
    value = await redis_client.get(key)
    return {key, value}
