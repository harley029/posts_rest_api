from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.config import settings
from src.entity.models import Comment, Post
from src.celery.celery_app import celery_app
from src.services.ai import generate_reply_sync
from src.repository.comments import get_comment_sync
from src.repository.posts import get_post_sync


DB_URL = f"postgresql+psycopg2://{settings.pg_user}:{settings.pg_password}@{settings.pg_domain}:{settings.pg_port}/{settings.pg_db}"
engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)


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
    with Session() as session:
        comment = get_comment_sync(comment_id, session)
        if not comment:
            return
        post = get_post_sync(comment.post_id, session)
        if not post or not post.automatic_reply_enabled:
            return
        reply_content = generate_reply_sync(post.content, comment.content)
        reply_comment = Comment(
            content=reply_content,
            post_id=post.id,
            user_id=post.user_id,
        )
        session.add(reply_comment)
        session.commit()
