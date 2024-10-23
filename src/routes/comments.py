from typing import List

from fastapi import APIRouter, HTTPException, Depends, status, Query

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.schemas.comment import CommentModel, CommentResponseSchema, CommentUpdateSchema
from src.entity.models import Post, Comment, User
from src.services.auth import auth_serviсe
from src.repository import comments as repository_comments
from src.services.profanity_checker import contains_profanity
from src.celery.worker import send_automatic_reply


router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("/", response_model=List[CommentResponseSchema])
async def get_comments(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all comments from the database.
    
    Parameters:
        - db (`AsyncSession`): An asynchronous database session.
    
    Returns:

        - List[CommentResponseSchema]**: A list of CommentResponseSchema objects representing all comments in the database.
    """
    comments = await repository_comments.get_comments(db)
    return comments


@router.post(
    "/", 
    response_model=CommentResponseSchema, 
    status_code=status.HTTP_201_CREATED
)
async def create_comment(
    body: CommentModel,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_serviсe.get_current_user),
):
    """
    Create a new comment for a specific post.

    Parameters:
        - body (CommentModel): A model representing the content and other details of the comment.
        - db (AsyncSession): An asynchronous database session.
        - user (User): The user who is creating the comment.#

    Returns:
        - CommentResponseSchema: A model representing the created comment.
    """
    post_result = await db.execute(select(Post).filter_by(id=body.post_id))
    post = post_result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    existing_comment_result = await db.execute(
        select(Comment).filter_by(content = body.content, post_id = body.post_id)
    )
    existing_comment = existing_comment_result.scalar_one_or_none()
    if existing_comment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment with the same content already exists for this post.",
        )
    is_censored = False
    if await contains_profanity(body.content):
        is_censored = True
        comment = await repository_comments.create_comment(
            body, db, user, censored=is_censored
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post contains inappropriate language.",
        )
    comment = await repository_comments.create_comment(
        body, db, user, censored=is_censored
    )
    # Створюємо коментар
    post = await db.get(Post, comment.post_id)
    if post.automatic_reply_enabled:
        delay_in_seconds = post.reply_delay * 60
        send_automatic_reply.apply_async(args=[comment.id], countdown=delay_in_seconds)

    return comment


@router.get("/censored", response_model=List[CommentResponseSchema])
async def get_censored_comments(
    limit: int = Query(default=10, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_serviсe.get_current_user),
):
    """
        Get all censored comments from the database.
    
        Parameters:
            - limit (int, default=10): The maximum number of comments to return.
            - offset (int, default=0): The index of the first comment to return.
            - db (AsyncSession): An asynchronous database session.
            - user (User): The user who is authorized to access the comments.
    
        Returns:
            - List[CommentResponseSchema] or []: A list of CommentResponseSchema objects representing all censored comments in the database, or an empty list if no censored comments are found.
    """
    comments = await repository_comments.get_censored_comments(limit, offset, db, user)
    return comments or []


@router.get("/{comment_id}", response_model=CommentResponseSchema)
async def get_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific comment by its ID.

    Parameters:
        - comment_id (int): The unique identifier of the comment to retrieve.
        - db (AsyncSession): An asynchronous database session.

    Returns:
        - CommentResponseSchema: A model representing the specific comment with its content, post ID, and user ID.
    """
    comment = await repository_comments.get_comment(comment_id, db)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment has not been found"
        )
    return comment


@router.put("/{comment_id}", response_model=CommentResponseSchema)
async def update_comment(
    comment_id: int,
    body: CommentUpdateSchema,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_serviсe.get_current_user),
):
    """
    Update an existing comment by its ID.

    Parameters:
        - comment_id (int): The unique identifier of the comment to update.
        - body (CommentUpdateSchema): A model representing the updated content and other details of the comment.
        - db (AsyncSession): An asynchronous database session.
        - user (User): The user who is authorized to update the comment.

    Returns:
        - CommentResponseSchema: A model representing the updated comment.
    """
    is_censored = False
    if await contains_profanity(body.content):
        is_censored = True
        comment = await repository_comments.update_comment(
            comment_id, body, db, user, censored=is_censored
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post contains inappropriate language.",
        )
    comment = await repository_comments.update_comment(
        comment_id, body, db, user, censored=is_censored
    )
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment has not been found")
    return comment


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_serviсe.get_current_user),
):
    """
    Delete a specific comment by its ID.

    Parameters:
        - comment_id (int): The unique identifier of the comment to delete.
        - db (AsyncSession): An asynchronous database session.
        - user (User): The user who is authorized to delete the comment.

    Returns:
        - CommentResponseSchema or None: The deleted comment object, or None if the comment was not found.
    """
    comment = await repository_comments.delete_comment(comment_id, db, user)
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment has not been found"
        )
    return comment
