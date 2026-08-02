# Change log

## chore<frontend>: adapt site image v0.4.1

## feat<frontend>: improve header layout and section user info v0.4.0

- Reworked the header layout for authenticated users (sticky top bar, more compact navigation, improved mobile behavior)
- Added a toggleable recipe search field to the header while keeping the Create action as a quick action
- Extracted the user information and sign-out functionality into the reusable SectionUserInfo component and integrated it into the Recipes, System, and Admin sections
  Updated the application to render the System section only when the user is authenticated
- Added a unit test for toggling the header search in frontend/src/components/AppHeader.test.tsx

## fix<frontend>: set url' as link v0.3.1

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
