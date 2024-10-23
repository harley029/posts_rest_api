from typing import List
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.user import UserResponseSchema
from src.schemas.comment import CommentResponseSchema


class StatusPostEnum(str, Enum):
    PUBLISHED = "published"
    DRAFT = "draft"


class PostSchema(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    content: str
    status: StatusPostEnum
    automatic_reply_enabled: bool = False
    reply_delay: int = 0

    model_config = ConfigDict(from_attributes=True)


class PostUpdateSchema(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    content: str
    status: StatusPostEnum
    automatic_reply_enabled: bool = False
    reply_delay: int = 0

    model_config = ConfigDict(from_attributes=True)


class PostResponseSchema(BaseModel):
    id: int = Field(ge=1)
    title: str
    content: str
    status: StatusPostEnum
    censored: bool
    user_id: int = Field(ge=1)  # UserResponseSchema
    # comments: List[CommentResponseSchema]

    model_config = ConfigDict(from_attributes=True)
