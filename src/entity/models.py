import enum
from datetime import date
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Integer, String, Boolean, Text, ForeignKey, Enum, func, DateTime
from sqlalchemy.orm import (
    declared_attr,
    Mapped,
    mapped_column,
    relationship,
)


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[date] = mapped_column(DateTime, default=func.now(), nullable=True)
    updated_at: Mapped[date] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=True)

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s"


class Post(Base):

    class StatusPost(str, enum.Enum):
        PUBLISHED = "published"
        DRAFT = "draft"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[StatusPost] = mapped_column(Enum(StatusPost), server_default=StatusPost.DRAFT.value, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    censored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    automatic_reply_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reply_delay: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # many to one mapping
    user: Mapped["User"] = relationship("User", back_populates="posts")
    # one to many mapping
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="post", cascade="all, delete-orphan")


class Comment(Base):
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"))
    censored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # many to one mapping
    user: Mapped["User"] = relationship("User", back_populates="comments", lazy="selectin")
    post: Mapped["Post"] = relationship("Post", back_populates="comments")


class User(Base):
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(255), nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)

    # one to many mapping
    posts: Mapped[list["Post"]] = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
