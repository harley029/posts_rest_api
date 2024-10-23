from pydantic import BaseModel, ConfigDict, Field

from src.schemas.user import UserResponseSchema


class CommentModel(BaseModel):
    content: str
    post_id: int = Field(ge=1)

    model_config = ConfigDict(from_attributes=True)


class CommentUpdateSchema(BaseModel):
    content: str
    model_config = ConfigDict(from_attributes=True)


class CommentResponseSchema(BaseModel):
    id: int = Field(ge=1)
    content: str
    user: UserResponseSchema
    censored: bool

    model_config = ConfigDict(from_attributes=True)
