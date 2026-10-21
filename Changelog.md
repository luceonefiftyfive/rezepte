# Change log

## [Unreleased]

- Return to the recipe overview with the browser's Back button after opening a recipe on mobile.

- Add formatting options for recipe instructions
  - Allow line breaks and bold or italic formatting in recipe instructions.
  - Preserve indented nested lists when importing instruction Markdown, including lettered sub-items.

## fix(frontend): reset recipe search and stabilize tests v0.10.1

- Clear the active recipe search when selecting "Alle" in the recipe overview.
- Store up to ten recent recipe searches locally in the browser and offer them from the search field.
- Add a single local test launcher and stabilize the signed recipe-image test.

## feat(backend): create thumbnails for existing recipe images v0.10.0

- Generate and store a thumbnail from an existing recipe image the first time its preview is requested.
- Report thumbnail storage failures instead of silently serving the original image as a thumbnail.

## fix(frontend): show recipe search on mobile v0.9.3

- Ensure the recipe search field is shown above page content and focused after tapping the search button on mobile browsers.

## fix(frontend): improve recipe print layout v0.9.2

- Arranged the recipe title, description, source, and metadata in the left column of the print layout.
- Stacked the QR code and recipe image in the right column; ingredients continue below across the full page width.

## fix(frontend): fractional ingredient amounts v0.9.1

- Display common decimal ingredient amounts as fractions: `0.5`/`0,5` as `½`, `0.3`/`0,3` and `0.33`/`0,33` as `⅓`,
  `0.25` as `¼`, and `0.125`/`0,125` as `⅛`.

## feat: rating handling v0.9.0

- Added per-user recipe ratings with one to five stars and an optional review of up to 200 characters.
- Ratings can be changed; recipe detail views now show the average score and written reviews in chronological order.
- Added authenticated rating endpoints, MongoDB uniqueness protection per recipe and user, backend coverage, and API documentation.

## feat(account): add self-service profile and password settings v0.8.0

- Added self-service account settings for updating the first name, last name, email address, and password.
- Password changes now invalidate existing sessions and require a new sign-in.
- Combined the user name, role, account settings, password change, and sign-out action into a hover menu; the
  password action opens and focuses the password form directly.
- Replaced the recipe overview reload text button with an accessible icon button and hover tooltip.
- Reworked the application header as a compact, full-width top bar with a responsive "Rezeptsammlung" title.
- Removed recipe-book selection and list-only labels from the recipe detail view.

## feat(frontend): inline recipe-book picker and larger recipe title v0.7.1

- Replaced the recipe-book selection dialog in the recipe editor with an inline multi-select picker,
  matching the tag picker; at least one recipe book remains required.
- Moved recipe-book and tag guidance to hover tooltips and aligned their neutral typography and form
  styling with the remaining editor fields.
- Recipe titles in the read-only detail view are now displayed as larger, responsive headings.

## feat(frontend): interactive tag picker with multi-select and creation v0.7.0

- Replaced free-text tag input in recipe editor with an interactive `TagPicker` combobox component.
- Supports selecting existing tags via dropdown checkboxes, deselecting tags via badge close buttons, and creating new
  tags with Enter.
- Rendered dropdown list directly underneath the tag input container.

## feat(frontend): select recipe books instead of free text v0.6.0

- Replaced the free-text "Gruppen-ID" input in user management with a dropdown listing the available, not-yet-assigned
  recipe books, both when creating a user and when adding a group role to an existing user.
- The "Gruppe hinzufügen" button is now disabled once all recipe books are already assigned to the user.
- Confirmed that renaming a recipe book already updates recipes and user management automatically, since both only
  reference the immutable group ID and resolve the display name dynamically.

## feat(backend): litestar backend v0.5.0

- Replace FastAPI thru litestar framework at backend,

## feat(frontend): add save and cancel actions to recipe editor header

- Added `Speichern` and `Abbrechen` actions to the header of the recipe creation and editing form.
- The save action remains disabled until the recipe draft has been changed.
- Added frontend tests for the dirty-state behavior and refreshing the overview after an edit is saved.

## fix(backend): make username login case-insensitive v0.4.4

- Login now accepts usernames regardless of uppercase/lowercase spelling.
- Added a regression test to cover login with mixed-case usernames.

## chore(frontend): add recipe print and PDF export v0.4.3

- Added a `Drucken (Print) / PDF` action in recipe detail view to open the browser print dialog.
- Added print-specific styles so the exported PDF focuses on recipe content and hides app navigation/actions.
- Added a frontend test to verify that the print action calls `window.print()`.

## chore(frontend): enable url links to receipe v0.4.2

- url of recipes can be copied and later directly used
- test is added

## chore(frontend): adapt site image v0.4.1

## feat(frontend): improve header layout and section user info v0.4.0

- Reworked the header layout for authenticated users (sticky top bar, more compact navigation, improved mobile behavior)
- Added a toggleable recipe search field to the header while keeping the Create action as a quick action
- Extracted the user information and sign-out functionality into the reusable SectionUserInfo component and integrated it
  into the Recipes, System, and Admin sections.Updated the application to render the System section only when the
  user is authenticated
- Added a unit test for toggling the header search in frontend/src/components/AppHeader.test.tsx

## fix(frontend): set url' as link v0.3.1

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
