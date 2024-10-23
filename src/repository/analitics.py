from datetime import datetime

from sqlalchemy import func, cast, Date, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.entity.models import Comment, User


async def get_comments_daily_breakdown(date_from: datetime, date_to: datetime, db: AsyncSession, user: User):
    """
    Retrieves a daily breakdown of the number of comments added within a specified period.

    Args:
    - date_from (datetime): The start of the period to count comments.
    - date_to (datetime): The end of the period to count comments.
    - db (AsyncSession): The database session.

    Returns:
    - dict: A dictionary where each key is a date, and the value is the number of comments on that date.
    """
    stmt = (
        select(
            cast(Comment.created_at, Date).label("date"),
            func.count(Comment.id).label("comment_count"),
        )
        .filter(
            Comment.created_at >= date_from,
            Comment.created_at <= date_to,
        )
        .filter_by(user_id=user.id)
        .group_by(cast(Comment.created_at, Date))
        .order_by("date")
    )

    result = await db.execute(stmt)
    daily_comments = result.fetchall()

    return {row.date: row.comment_count for row in daily_comments}
