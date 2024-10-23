from datetime import datetime

from fastapi import Query
from fastapi import APIRouter, Depends, Query

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.repository import analitics as repository_posts
from src.entity.models import User
from src.services.auth import auth_serviсe


router = APIRouter(prefix="/analitics", tags=["analitics"])


@router.get("/daily-breakdown", response_model=dict)
async def get_comments_daily_breakdown(
    date_from: datetime = Query(..., alias="date_from"),
    date_to: datetime = Query(..., alias="date_to"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_serviсe.get_current_user),
):
    """
    Retrieve a daily breakdown of comment counts for posts within a specified period.

    Parameters:
    - date_from (datetime): The start date of the period to count comments.
    - date_to (datetime): The end date of the period to count comments.
    - db (AsyncSession): The database session to use for the operation.

    Returns:
    - dict: A dictionary where each key is a date, and the value is the number of comments on that date.
    """
    daily_breakdown = await repository_posts.get_comments_daily_breakdown(
        date_from, date_to, db, user
    )
    return daily_breakdown
