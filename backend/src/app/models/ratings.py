from datetime import datetime

from pydantic import BaseModel, Field


class RecipeRatingInput(BaseModel):
    score: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=200)


class RecipeRatingOut(RecipeRatingInput):
    username: str
    created_at: datetime
    updated_at: datetime


class RecipeRatingsOut(BaseModel):
    average_score: float | None
    rating_count: int
    own_rating: RecipeRatingOut | None
    comments: list[RecipeRatingOut]
