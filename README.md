# rezepte

New recipes app - successor of [previous recipe app variant](https://github.com/luceonefiftyfive/recipes)

## Goal

General target vision is a **family recipe collection** as a private, multi-user recipe database with different recipe books.
Users can read, search for, create, and edit recipes, in particular with visualization through appealing images.

The final product is supposed to be available as an web app, working on all kinds of devices, under the following adress:

- `https://rezepte.unbenet.de`
- As an additional name (optional!): `https://unbekocht.de`
- For a dev-system, to test new updates: `https://dev-rezepte.unbenet.de`

The system should be containerized (Docker), run on a remote server, be easy to deploy, and get backuped regularly to a local server.

## Account settings

Authenticated users can manage their own first name, last name, and email address in the System section under "Mein Konto". Their name and user name form a menu button in each section header. Hovering over it, or activating it with a click, reveals the role, "Einstellungen", "Passwort ändern", and "Abmelden" actions. The settings actions open the relevant account form directly.
Changing a password requires the current password and confirmation of the new password. After a successful password change, the user is signed out and must sign in again with the new password.
In the recipe overview, the reload action is shown as a circular reload icon. Its label is displayed as a tooltip on hover and remains available to assistive technologies.

## Recipe ratings

When reading a recipe, every authenticated user can give it one to five stars and add an optional review of up to 200 characters. A later submission updates that user's existing rating. The detail view shows the average score and all written reviews in chronological order. The overview does not show ratings.

The API and data contract are described in [Recipe ratings](docs/backend/recipe-ratings.md).

## Additional information

### Docker commands

Common Docker and deployment commands are documented here:

- [Docker commands](docs/docker-commands.md)
- [Docker commands to update certficate](docs/certificate-renewal.md)

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
