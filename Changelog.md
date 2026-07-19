# Change log

## fix: refresh recipe overview automatically v0.3.0

- Automatically refresh the recipe overview after creating, updating, or deleting a recipe.

## feature: add authentication

- replace backend `Keycload` authentication fuctionality with "own" backend functionality
  - new functionality is described in `docs\backend\user-management-api.md`
  - add unit test for bringup
    - see `backend/tests`
- splot python backend in several files per functionality
