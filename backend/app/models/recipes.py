from pydantic import BaseModel, Field


class RecipeIn(BaseModel):
    title: str = Field(..., min_length=1)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class RecipeOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: str
