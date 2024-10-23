from typing import List

from fastapi import APIRouter, HTTPException, Depends, status, Query

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.schemas.post import PostResponseSchema, PostSchema, PostUpdateSchema, StatusPostEnum
from src.schemas.comment import CommentResponseSchema
from src.repository import posts as repository_posts
from src.entity.models import User
from src.services.auth import auth_serviсe
from src.services.profanity_checker import contains_profanity


router = APIRouter(prefix='/posts', tags=["posts"])


@router.get("/", response_model=List[PostResponseSchema])
async def get_posts(
    limit: int = Query(default=10, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a list of posts.

    Parameters:
    - skip (int): The number of posts to skip. Default is 0.
    - limit (int): The maximum number of posts to return. Default is 100.
    - offset (int): The index of the first contact to retrieve. Default is 0.
    - db (Session): The database session. It is obtained using the `get_db` dependency.
    - user (User): The authenticated user making the request.

    Returns:
    - List[PostResponseSchema]: A list of posts.
    """
    posts = await repository_posts.get_posts(limit, offset, db)
    return posts


@router.get("/censored", response_model=List[PostResponseSchema])
async def get_censored_posts(
    limit: int = Query(default=10, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_serviсe.get_current_user),
):
    """
    Retrieve a list of posts where censored = True.

    Parameters:
    - limit (int): The maximum number of posts to return.
    - offset (int): The index of the first post to retrieve.

    Returns:
    - List[PostResponseSchema]: A list of censored posts.
    """
    posts = await repository_posts.get_censored_posts(limit, offset, db)
    return posts


@router.get("/{post_id}", response_model=PostResponseSchema)
async def get_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a specific post by its ID.

    Parameters:
    - post_id (int): The unique identifier of the post to retrieve.
    - db (AsyncSession): The database session to use for the operation.

    Returns:
    - PostResponseSchema: The data of the specific post. If the post is not found, an HTTPException with status code 404 and detail "Post not found" is raised.
    """
    post = await repository_posts.get_post(post_id, db)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post(
    "/", 
    response_model=PostResponseSchema,
    status_code=status.HTTP_201_CREATED 
)
async def create_post(
    body: PostSchema,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_serviсe.get_current_user),
):
    """
    Create a new post.

    Parameters:
    - body (PostSchema): The data of the new post to be created.
    - db (AsyncSession): The database session to use for the operation.
    - user (User): The authenticated user making the request.

    Returns:
    - ContactResponseSchema: The newly created contact data.
    """
    # Проверяем пост на нецензурную лексику
    is_censored = False
    if await contains_profanity(body.title) or await contains_profanity(body.content):
        is_censored = True
        post = await repository_posts.create_post(body, db, user, censored=is_censored)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post contains inappropriate language.",
        )
    post = await repository_posts.create_post(body, db, user, censored=is_censored)
    return post


@router.put("/{post_id}", response_model=PostResponseSchema)
async def update_post(
    body: PostUpdateSchema,
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_serviсe.get_current_user),
):
    """
    Update an existing post.

    Parameters:
    - body (PostUpdateSchema): The updated post data.
    - post_id (int): The ID of the post to update.
    - db (AsyncSession): The database session to use for the operation.
    - user (User): The authenticated user making the request.

    Returns:
    - PostResponseSchema: The updated post data.
    - HTTPException: If the post with the specified ID is not found.
    """
    # Проверяем пост на нецензурную лексику
    is_censored = False
    if await contains_profanity(body.title) or await contains_profanity(body.content):
        is_censored = True
        post = await repository_posts.update_post(
            post_id, body, db, user, censored=is_censored
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post contains inappropriate language.",
        )
    post = await repository_posts.update_post(
        post_id, body, db, user, censored=is_censored
    )
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post has not been found"
        )
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_serviсe.get_current_user),
):
    """
    Delete a post by its ID.

    Parameters:
    - post_id (int): The ID of the post to delete.
    - db (AsyncSession): The database session to use for the operation.
    - user (User): The authenticated user making the request.

    Returns:
    - PostResponseSchema: The deleted post data.
    - HTTPException: If the contact with the specified ID is not found.
    """
    post = await repository_posts.delete_post(post_id, db, user)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post has not been found"
        )
    return post


@router.get("/{post_id}/comments", response_model=List[CommentResponseSchema])
async def get_post_comments(
    post_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
        Retrieve the comments of a specific post.
    
        Parameters:
        - post_id (int): The unique identifier of the post for which the comments are to be retrieved.
        - db (AsyncSession): The database session to use for the operation.
    
        Returns:
        - List[CommentResponseSchema]: A list of comments associated with the specified post. If no comments are found, an empty list is returned.
    """
    post = await repository_posts.get_post(post_id, db)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post has not been found"
        )

    comments = await repository_posts.get_post_comments(post_id, db)
    return comments or []


@router.get("/{post_id}/status", response_model=StatusPostEnum)
async def get_post_status(
    post_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve the status of a specific post.

    Parameters:
    - post_id (int): The ID of the post for which the status is to be retrieved.
    - db (AsyncSession): The database session to use for the operation.

    Returns:
    - StatusPostEnum: The status of the post.
    """
    post_status = await repository_posts.get_post_status(post_id, db)
    if post_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post has not been found"
        )
    return post_status


@router.put("/{post_id}/status", response_model=PostResponseSchema)
async def update_post_status(
    post_id: int,
    new_status: StatusPostEnum,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_serviсe.get_current_user),
):
    """
    Update the status of a specific post.

    Parameters:
    - post_id (int): The ID of the post to update the status.
    - new_status (StatusPostEnum): The new status to set for the post.
    - db (AsyncSession): The database session to use for the operation.

    Returns:
    - PostResponseSchema: The updated post data with the new status.
    """
    post = await repository_posts.update_post_status(post_id, new_status, db, user)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post has not been found"
        )
    return post
