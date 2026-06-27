# rezepte

New recipes app - successor of [previous recipe app variant](https://github.com/luceonefiftyfive/recipes)

<p align="center">
  <img src="./frontend/assets/rezepte-logo-sage.png" alt="Rezepte logo" width="120" />
</p>

## Goal

General target vision is a **family recipe collection** as a private, multi-user recipe database with different recipe books.
Users can read, search for, create, and edit recipes, in particular with visualization through appealing images.

The final product is supposed to be available as an web app, working on all kinds of devices, under the following adress:

- `https://rezepte.unbenet.de`
- As an additional name (optional!): `https://unbekocht.de`
- For a dev-system, to test new updates: `https://dev-rezepte.unbenet.de`

The system should be containerized (Docker), run on a remote server, be easy to deploy, and get backuped regularly to a local server.

## Additional information

### Docker commands

Common Docker and deployment commands are documented here:

[Docker commands](docs/docker-commands.md)

### Formatting in the repository

Set up automatic formatting for the whole repository to ensure a consistent code style across all file types.

See: [Formatting in VS Code](./docs/formatting.md)
