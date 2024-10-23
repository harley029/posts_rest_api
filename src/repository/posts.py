from fastapi import HTTPException, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.entity.models import Post, Comment, User
from src.schemas.post import PostSchema, PostUpdateSchema, StatusPostEnum


async def get_posts(limit: int, offset: int, db: AsyncSession):
    """
    Retrieves a list of posts for the specified user within the specified limit and offset.

    Args:
    - limit (int): The maximum number of posts to retrieve.
    - offset (int): The index from which to start retrieving posts.
    - db (AsyncSession): The database session.
    - user (User): The user for whom the posts are being retrieved.

    Returns:
    - list: A list of Post objects for the specified user within the specified limit and offset.
    """
    stmt = (
        select(Post)
        .filter_by(status=StatusPostEnum.PUBLISHED, censored=False)
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    posts = result.scalars().all()
    return posts


async def get_censored_posts(limit: int, offset: int, db: AsyncSession):
    """
    Retrieves a list of posts with censored = True within the specified limit and offset.

    Args:
    - limit (int): The maximum number of posts to retrieve.
    - offset (int): The index from which to start retrieving posts.
    - db (AsyncSession): The database session.

    Returns:
    - list: A list of Post objects with censored = True within the specified limit and offset.
    """
    stmt = select(Post).filter_by(censored = True).offset(offset).limit(limit)
    result = await db.execute(stmt)
    posts = result.scalars().all()
    return posts


async def get_post(post_id: int, db: AsyncSession):
    """
    Retrieves a specific post by its id for the specified user.

    Args:
    - post_id (int): The id of the contact to retrieve.
    - db (AsyncSession): The database session.
    - user (User): The user for whom the contact is being retrieved.

    Returns:
    - Post or None: The specific contact object for the specified user and post_id, or None if not found.
    """
    stmt = select(Post).filter_by(id=post_id)
    result = await db.execute(stmt)
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post has not been found",
        )
    return post


async def create_post(
    body: PostSchema, 
    db: AsyncSession, 
    user: User, 
    censored: bool = False
):
    """
    Creates a new post for the specified user.

    Args:
    - body (PostSchema): The schema containing the details of the new post.
    - db (AsyncSession): The database session.
    - user (User): The user for whom the contact is being created.

    Raises:
    - HTTPException: If a post with the same title and content already exists.

    Returns:
    - Post: The newly created post object.
    """
    existing_post = await db.execute(
        select(Post).filter_by(title=body.title, content=body.content)
    )
    existing_post = existing_post.scalar_one_or_none()
    if existing_post:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post is already exist",
        )
    post = Post(**body.model_dump(), user_id=user.id, censored=censored)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def update_post(
    post_id: int,
    body: PostUpdateSchema,
    db: AsyncSession,
    user: User,
    censored: bool = False
):
    """
    Updates a specific post by its id for the specified user.

    Args:
    - post_id (int): The id of the post to update.
    - body (PostUpdateSchema): The schema containing the details of the updated post.
    - db (AsyncSession): The database session.
    - user (User): The user for whom the contact is being updated.

    Returns:
    - Post: The updated post object.
    """
    stmt = select(Post).filter_by(id=post_id, user_id=user.id)
    result = await db.execute(stmt)
    post = result.scalar_one_or_none()
    if post is None:
        return None
    for key, value in body.model_dump().items():
        setattr(post, key, value)
    post.censored = censored
    await db.commit()
    await db.refresh(post)
    return post


async def delete_post(post_id: int, db: AsyncSession, user: User):
    """
    Deletes a specific post by its id for the specified user.

    Args:
    - post_id (int): The id of the post to delete.
    - db (AsyncSession): The database session.
    - user (User): The user for whom the contact is being deleted.

    Returns:
    - Post or None: The specific post object for the specified user and contact_id, or None if not found.
    """
    stmt = select(Post).filter_by(id=post_id, user_id=user.id)
    result = await db.execute(stmt)
    post = result.scalar_one_or_none()
    if post:
        await db.delete(post)
        await db.commit()
    return post


async def get_post_comments(post_id: int, db: AsyncSession):
    """
    Retrieves a list of comments for a specific post.

    Args:
    - post_id (int): The id of the post for which to retrieve comments.
    - db (AsyncSession): The database session.

    Returns:
    - list: A list of Comment objects for the specified post.
    """
    stmt = select(Comment).filter_by(post_id = post_id, censored = False)
    result = await db.execute(stmt)
    comments = result.scalars().all()
    return comments


async def get_post_status(post_id: int, db: AsyncSession):
    """
    Retrieves the status of a specific post by its id.

    Args:
    - post_id (int): The id of the post to retrieve the status.
    - db (AsyncSession): The database session.

    Returns:
    - StatusPost or None: The status of the post or None if not found.
    """
    stmt = select(Post.status).filter_by(id=post_id)
    result = await db.execute(stmt)
    status = result.scalar_one_or_none()
    return status


async def update_post_status(
    post_id: int, 
    new_status: StatusPostEnum, 
    db: AsyncSession, 
    user: User
):
    """
    Updates the status of a specific post by its id.

    Args:
    - post_id (int): The id of the post to update the status.
    - new_status (StatusPostEnum): The new status to set for the post.
    - db (AsyncSession): The database session.

    Returns:
    - Post: The updated post object with the new status.
    """
    stmt = select(Post).filter_by(id=post_id, user_id=user.id)
    result = await db.execute(stmt)
    post = result.scalar_one_or_none()
    if post is None:
        return None

    post.status = new_status
    await db.commit()
    await db.refresh(post)
    return post
