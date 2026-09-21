# Recipe Ratings

Base URL: `http://<server>/api`

Recipe ratings are available only to authenticated users who may read the recipe. Ratings are shown only in the recipe detail view.

## Behavior

- Every user has exactly one rating per recipe.
- A rating contains a score from 1 through 5 and an optional comment of up to 200 characters.
- Sending another rating for the same recipe updates the existing score and comment.
- The detail response contains the average score, the number of ratings, the caller's own rating, and comments in creation order.
- Ratings without a comment contribute to the average but are not included in `comments`.

## Read Ratings

```http
GET /recipes/{recipe_id}/ratings
Authorization: Bearer <ACCESS_TOKEN>
```

### Response `200 OK`

```json
{
  "average_score": 4.5,
  "rating_count": 2,
  "own_rating": {
    "score": 5,
    "comment": "Spitzenrezept",
    "username": "jdoe",
    "created_at": "2026-09-21T12:00:00Z",
    "updated_at": "2026-09-21T12:00:00Z"
  },
  "comments": [
    {
      "score": 5,
      "comment": "Spitzenrezept",
      "username": "jdoe",
      "created_at": "2026-09-21T12:00:00Z",
      "updated_at": "2026-09-21T12:00:00Z"
    }
  ]
}
```

`average_score` is `null` and `own_rating` is `null` when no ratings exist.

## Create or Update a Rating

```http
PUT /recipes/{recipe_id}/rating
Authorization: Bearer <ACCESS_TOKEN>
Content-Type: application/json
```

```json
{
  "score": 5,
  "comment": "Spitzenrezept"
}
```

### Response `200 OK`

Returns the saved rating with `username`, `created_at`, and `updated_at`.

### Validation and Errors

| Status | Meaning                                                           |
| ------ | ----------------------------------------------------------------- |
| `401`  | Missing or invalid authentication                                 |
| `404`  | Recipe does not exist or is not available to the current user     |
| `422`  | `score` is outside 1-5 or `comment` is longer than 200 characters |
