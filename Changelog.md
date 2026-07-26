# Change log

## feat: add source information to recipes v0.3.0

- add field source to recipes
- add documentaion of database structure in [docs/backend/database-structure.md](docs/backend/database-structure.md)

## fix: refresh recipe overview automatically v0.2.4

- Automatically refresh the recipe overview after creating, updating, or deleting a recipe.

## feature: add authentication

- replace backend `Keycload` authentication fuctionality with "own" backend functionality
  - new functionality is described in `docs\backend\user-management-api.md`
  - add unit test for bringup
    - see `backend/tests`
- splot python backend in several files per functionality
