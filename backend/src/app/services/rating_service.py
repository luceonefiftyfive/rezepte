from datetime import datetime, timezone

from app.models.ratings import RecipeRatingInput, RecipeRatingOut, RecipeRatingsOut
from app.repositories.rating_repository import RatingRepository
from motor.motor_asyncio import AsyncIOMotorDatabase


class RatingService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.repository = RatingRepository(db)

    @staticmethod
    def _to_output(document: dict) -> RecipeRatingOut:
        return RecipeRatingOut.model_validate(
            {key: value for key, value in document.items() if key != "_id"}
        )

    async def get_ratings(self, recipe_id: str, user_id: str) -> RecipeRatingsOut:
        documents = await self.repository.list_for_recipe(recipe_id)
        ratings = [self._to_output(document) for document in documents]
        average_score = (
            sum(rating.score for rating in ratings) / len(ratings) if ratings else None
        )
        own_rating = next(
            (
                rating
                for document, rating in zip(documents, ratings, strict=True)
                if document["user_id"] == user_id
            ),
            None,
        )
        return RecipeRatingsOut(
            average_score=average_score,
            rating_count=len(ratings),
            own_rating=own_rating,
            comments=[rating for rating in ratings if rating.comment],
        )

    async def save_rating(
        self,
        recipe_id: str,
        user_id: str,
        username: str,
        rating: RecipeRatingInput,
    ) -> RecipeRatingOut:
        document = await self.repository.upsert_rating(
            recipe_id=recipe_id,
            user_id=user_id,
            username=username,
            score=rating.score,
            comment=rating.comment.strip(),
            now=datetime.now(timezone.utc),
        )
        return self._to_output(document)
