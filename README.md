# rezepte

New recipes app - successor of [previous recipe app variant](https://github.com/luceonefiftyfive/recipes)

## Goal

General target vision is a **family recipe collection** as a private, multi-user recipe database with different recipe books.
Users can read, search for, create, and edit recipes, in particular with visualization through appealing images.

The final product is intended to be available as a web app that works on all kinds of devices at the following addresses:

- `https://rezepte.unbenet.de`
- As an additional name (optional!): `https://unbekocht.de`
- For a development system to test updates: `https://dev-rezepte.unbenet.de`

The system should be containerized with Docker, run on a remote server, be easy to deploy, and be backed up regularly
to a local server.

## Account settings

Authenticated users can manage their first name, last name, and email address in the System section under
"Mein Konto" (My Account). Their name and username appear in a menu button in each section header. Hovering
over it or clicking it reveals their role and the "Einstellungen" (Settings), "Passwort ändern" (Change password),
and "Abmelden" (Sign out) actions. The settings actions open the corresponding account form directly.
Changing a password requires the current password and confirmation of the new password. After a successful password
change, the user is signed out and must sign in again with the new password.
In the recipe overview, the reload action is shown as a circular reload icon. Its label is displayed as a tooltip
on hover and remains available to assistive technologies.

## Recipe ratings

When reading a recipe, every authenticated user can give it one to five stars and add an optional review of up
to 200 characters. A later submission updates that user's existing rating. The detail view shows the average score
and all written reviews in chronological order. The overview does not show ratings.

The API and data contract are described in [Recipe ratings](docs/backend/recipe-ratings.md).

## Recipe instruction formatting

Recipe instructions support line breaks, **bold** (`**text**`), _italic_ (`*text*`), and nested lists. When
importing instruction Markdown, each unindented list item becomes a recipe step; indent sub-items by at least
two spaces to keep them within that step. Bullet markers (`-`, `*`, `+`), numbered markers (`1.`), and
lettered markers (`a)`) are supported. For example:

```md
1. Test

- This is part 1.1
  a) This is part 1.1.1
  b) This is part 1.1.2
- This is part 1.2

2. Next step
```

## Additional information

### Docker commands

Common Docker and deployment commands are documented here:

- [Docker commands](docs/docker-commands.md)
- [Docker commands to renew certificates](docs/certificate-renewal.md)

### Formatting in the repository

Set up automatic formatting for the whole repository to ensure a consistent code style across all file types.

See: [Formatting in VS Code](./docs/formatting.md)

### System version

The system version is configured centrally in `version.yaml` at repository root:

```yaml
version: 0.1.0
```

The backend exposes this value together with the current git hash via `/api/system/version`.
In the frontend, the same information is available in the header hamburger menu under "Version".

See document [Creating a Release](docs/creation-release.md) for more details.
