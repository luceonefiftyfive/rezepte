# Generic MongoDB Repository

`app.repositories.base_repository.MongoRepository` provides common asynchronous
MongoDB document operations:

- `find_by_id`
- `find_one`
- `exists`
- `count`
- `insert`
- `list` with filtering, sorting, skip and limit
- `update_by_id`
- `update_one`
- `delete_by_id`

Entity repositories configure a collection name and add domain-specific methods:

```python
from typing import Any

from app.repositories.base_repository import MongoRepository

RecipeDocument = dict[str, Any]


class RecipeRepository(MongoRepository[RecipeDocument]):
    collection_name = "recipes"

    async def find_by_normalized_name(self, name: str) -> RecipeDocument | None:
        return await self.find_one({"normalized_name": name})
```

The existing `UserRepository` now inherits from this base class.

## Setup and tests

```bash
uv sync --group dev
uv run pytest -q src/tests/test_base_repository.py
```

The source layout is configured in `pyproject.toml`, so `uv run pytest` can import
`app` without manually setting `PYTHONPATH`.
