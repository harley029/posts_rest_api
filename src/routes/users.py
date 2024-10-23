from fastapi import APIRouter, Depends

from src.database.db import get_db
from src.entity.models import User
from src.schemas.user import UserResponseSchema
from src.schemas.user import UserDb
from src.services.auth import auth_serviсe


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponseSchema)
async def get_current_user(user: User = Depends(auth_serviсe.get_current_user)):
    """
    Retrieves the current authenticated user's information.

    Parameters:
    - user (User): The authenticated user object obtained from the auth_service.

    Returns:
    - UserResponseSchema: The current authenticated user's information in the specified response model format.

    This endpoint is protected by a rate limiter that allows no more than 2 requests per 10 seconds.
    """
    return user

