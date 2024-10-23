from fastapi import Depends, HTTPException, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.entity.models import User
from src.schemas.user import UserSchema


async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieves a user from the database by their email address.

    Args:
    - email (str): The email address of the user to retrieve.
    - db (AsyncSession, optional): The database session to use for the query. Defaults to Depends(get_db).

    Returns:
    - User | None: The user object if found, otherwise None.

    Raises:
    - HTTPException: If an error occurs while retrieving the user.
    """
    stmt = select(User).filter_by(email=email)
    user = await db.execute(stmt)
    user = user.scalar_one_or_none()
    return user


async def create_user(body: UserSchema, db: AsyncSession = Depends(get_db)):
    """
    Creates a new user in the database.

    Args:
    - body (UserSchema): The user schema containing the user's data.
    - db (AsyncSession, optional): The database session to use for the query. Defaults to Depends(get_db).

    Returns:
    - User: The newly created user object.

    Raises:
    - HTTPException: If an error occurs while creating the user.

    This function first generates an avatar for the user using the Gravatar library. If an error occurs during this process, it raises an HTTPException with a status code of 500 (Internal Server Error). It then creates a new User object using the data from the provided UserSchema, sets the avatar, and adds it to the database session. Finally, it commits the changes to the database and refreshes the user object before returning it.
    """
    existing_user = await db.execute(select(User).filter_by(email=body.email))
    existing_user = existing_user.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already exists",
        )

    new_user = User(**body.model_dump())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def update_token(user: User, refresh_token: str | None, db: AsyncSession):
    """
    Updates the refresh token for the given user in the database.

    Args:
    - user (User): The user object to update the refresh token for.
    - refresh_token (str | None): The new refresh token to set for the user, or None to remove the refresh token.
    - db (AsyncSession): The database session to use for the update.

    Returns:
    - None: This function does not return a value.

    Raises:
    - None: This function does not raise any exceptions.

    This function updates the refresh token for the given user in the database. If refresh_token is None, the refresh token for the user is removed. The changes are then committed to the database.
    """
    user.refresh_token = refresh_token
    await db.commit()


async def confirmed_email(email: str, db: AsyncSession):
    """
    Confirms the email for the given user in the database.

    Args:
    - email (str): The email address of the user to confirm.
    - db (AsyncSession): The database session to use for the update.

    Returns:
    - None: This function does not return a value.

    Raises:
    - None: This function does not raise any exceptions.

    This function confirms the email for the given user in the database. It retrieves the user object from the database using the provided email address, sets the `confirmed` attribute of the user to `True`, and then commits the changes to the database. Finally, it refreshes the user object to ensure that the changes are reflected in the returned object.
    """
    user = await get_user_by_email(email, db)
    user.confirmed = True
    await db.commit()
    await db.refresh(user)


async def update_password(user: User, new_password: str, db: AsyncSession):
    """
    Updates the password for the given user in the database.

    Args:
    - user (User): The user object to update the password for.
    - new_password (str): The new password to set for the user.
    - db (AsyncSession): The database session to use for the update.

    Returns:
    - User: The updated user object with the new password.

    Raises:
    - None: This function does not raise any exceptions.

    This function updates the password for the given user in the database. It retrieves the user object from the database using the provided user object, sets the `password` attribute of the user to the new password, and then commits the changes to the database. Finally, it refreshes the user object to ensure that the changes are reflected in the returned object.
    """
    user.password = new_password
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
