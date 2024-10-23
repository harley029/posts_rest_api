import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.database.db import DB_URL
from src.entity.models import Comment, Post
from src.services.ai import generate_reply
from src.celery.celery_app import celery_app


engine = create_async_engine(DB_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)


@celery_app.task
def send_automatic_reply(comment_id: int):
    """
    This task is responsible for sending an automatic reply to a comment.

    Parameters:
    - comment_id (int): The ID of the comment to which the automatic reply will be sent.

    Returns:
    - None: This function does not return any value. It sends an automatic reply to the specified comment.
    The function first creates a new event loop and sets it as the current event loop. Then, it runs the `process_reply` function asynchronously using the event loop. Finally, it closes the event loop.#+
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(process_reply(comment_id))
    finally:
        loop.close()


async def process_reply(comment_id: int):
    """
    This task is responsible for sending an automatic reply to a comment.
    This asynchronous function is responsible for creating and adding a new comment as an automatic reply to an existing comment.

    Parameters:
    - comment_id (int): The ID of the comment to which the automatic reply will be sent.

    Returns:
    - None: This function does not return any value. It sends an automatic reply to the specified comment.
    The function first creates a new event loop and sets it as the current event loop. Then, it runs the `process_reply` function asynchronously using the event loop. Finally, it closes the event loop.
    - None: This function does not return any value. It creates and adds a new comment as an automatic reply to the specified comment.

    The function first retrieves the comment and its associated post from the database using the provided comment ID. If the comment or its associated post does not exist, the function returns without performing any further actions. If the post exists and its automatic reply feature is enabled, the function generates a reply content using the `generate_reply` function. Then, it creates a new Comment object with the generated reply content, the ID of the associated post, and the ID of the associated user. Finally, the new comment object is added to the database session and committed to the database.
    """
    async with async_session() as session:
        comment = await session.get(Comment, comment_id)
        if not comment:
            return
        post = await session.get(Post, comment.post_id)
        if not post or not post.automatic_reply_enabled:
            return
        reply_content = await generate_reply(post.content, comment.content)
        reply_comment = Comment(
            content=reply_content,
            post_id=post.id,
            user_id=post.user_id,
        )
        session.add(reply_comment)
        await session.commit()
