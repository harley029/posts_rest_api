from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.entity.models import Post, Comment, User
from src.schemas.comment import CommentModel, CommentResponseSchema, CommentUpdateSchema


async def get_comments(db: AsyncSession):
    """
    Retrieves all uncensored comments from the database.

    Args: 
        -db (AsyncSession): The database session.
    
    Returns: 
        - list: A list of uncensored Comment objects.
    """
    stmt = select(Comment).filter_by(censored = False)
    result = await db.execute(stmt)
    comments = result.scalars().all()
    return comments


async def create_comment(
    body: CommentModel, 
    db: AsyncSession, 
    user: User, 
    censored: bool = False
):
    """
    Creates a new comment in the database and associates it with the provided user.

    Args:
        - body (CommentModel): The data for the new comment.
        - db (AsyncSession): The database session.
        - user (User): The user who is creating the comment.
        - censored (bool): A flag indicating whether the comment should be censored. Default is False.

    Returns: 
        - Comment: The newly created comment object.
    """
    comment = Comment(**body.model_dump(), user_id=user.id, censored=censored)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


async def get_censored_comments(limit: int, offset: int, db: AsyncSession, user: User):
    """
    Retrieves all censored comments with pagination.

    Args:
        - limit (int): The maximum number of comments to retrieve.
        - offset (int): The index from which to start retrieving comments.
        - db (AsyncSession): The database session.

    Returns: 
        - list: A list of censored Comment objects.
    """
    stmt = select(Comment).filter_by(user_id=user.id, censored = True).offset(offset).limit(limit)
    result = await db.execute(stmt)
    comments = result.scalars().all()
    return comments


async def get_comment(comment_id: int, db: AsyncSession):
    """
    Retrieves a specific comment from the database by its ID.

    Args:
        - comment_id (int): The unique identifier of the comment to retrieve.
        - db (AsyncSession): The database session.

    Returns: 
        - Comment: The Comment object with the specified ID, or None if the comment does not exist.
    """
    stmt = select(Comment).filter_by(id = comment_id)
    result = await db.execute(stmt)
    comment = result.scalar_one_or_none()
    return comment


async def update_comment(
    comment_id: int,
    body: CommentUpdateSchema,
    db: AsyncSession,
    user: User,
    censored: bool = False
):
    """
    Updates an existing comment in the database and associates it with the provided user.

    Args:
        - comment_id (int): The unique identifier of the comment to update.
        - body (CommentUpdateSchema): The data for the updated comment.
        - db (AsyncSession): The database session.
        - user (User): The user who is updating the comment.
        - censored (bool): A flag indicating whether the comment should be censored. Default is False.

    Returns: 
        - Comment: The updated Comment object.
    """
    stmt = select(Comment).filter_by(id=comment_id, user_id=user.id)
    result = await db.execute(stmt)
    comment = result.scalar_one_or_none()
    if comment is None:
        return None
    for key, value in body.model_dump().items():
        setattr(comment, key, value)
    comment.censored = censored
    await db.commit()
    await db.refresh(comment)
    return comment


async def delete_comment(
        comment_id: int, 
        db: AsyncSession, 
        user: User
    ):
    """
    Deletes a comment from the database by its ID and associated with the provided user.

    Args:
        - comment_id (int): The unique identifier of the comment to delete.
        - db (AsyncSession): The database session.
        - user (User): The user who is deleting the comment.

    Returns: 
        - Comment | None: The deleted Comment object if the comment exists, otherwise None.
    """
    stmt = select(Comment).filter_by(id=comment_id, user_id=user.id)
    result = await db.execute(stmt)
    comment = result.scalar_one_or_none()
    if comment:
        await db.delete(comment)
        await db.commit()
    return comment
