# Formatting setup

This project uses VS Code formatters to keep Markdown, frontend, Python, JSON, YAML, and Docker-related files consistent.

## Recommended VS Code extensions

| File format                     | Formatter / Tool | VS Code extension         | Extension ID                      |
| ------------------------------- | ---------------- | ------------------------- | --------------------------------- |
| Markdown, incl. tables          | Prettier         | Prettier - Code formatter | `esbenp.prettier-vscode`          |
| ==                              | Markdownlint     | Markdownlint              | `DavidAnson.vascode-markdownlint` |
| TSX / CSS / JSON / JSONC / YAML | Prettier         | Prettier - Code formatter | `esbenp.prettier-vscode`          |
| Python                          | Black Formatter  | Python                    | `ms-python.python`                |
| ==                              | ==               | Black Formatter           | `ms-python.black-formatter`       |
| Python imports / lint fixes     | Ruff             | Ruff by Astral Software   | `charliermarsh.ruff`              |
| Dockerfile / compose.yaml       | Container Tools  | Container Tools           | `ms-azuretools.vscode-containers` |
| ==                              | Docker DX        | Docker DX                 | `docker.docker`                   |

## Install extensions

```bash
code --install-extension esbenp.prettier-vscode
code --install-extension DavidAnson.vscode-markdownlint
code --install-extension ms-python.python
code --install-extension ms-python.black-formatter
code --install-extension charliermarsh.ruff
code --install-extension ms-azuretools.vscode-containers
code --install-extension docker.docker
```

## VS Code settings

Create or update: `.vscode/settings.json`

```jsonc
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",

  "prettier.printWidth": 100,
  "prettier.singleQuote": true,
  "prettier.trailingComma": "all",
  "prettier.objectWrap": "preserve",

  "[markdown]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.wordWrap": "on",
    "files.trimTrailingWhitespace": false,
  },

  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
  },
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
  },
  "[javascriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
  },
  "[css]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
  },
  "[json]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
  },
  "[jsonc]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
  },
  "[yaml]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
  },

  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports.ruff": "explicit",
      "source.fixAll.ruff": "explicit",
    },
  },

  "[dockercompose]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
  },
  "[dockerfile]": {
    "editor.formatOnSave": false,
  },
}
```

## Notes

- Prettier is used for Markdown, tables, frontend files, JSON, JSONC, and YAML.
- Black Formatter is used for Python formatting.
- Ruff by Astral Software is used for Python import sorting and lint fixes.
- Dockerfiles are not auto-formatted aggressively; they are handled mainly with linting and IntelliSense.
- `prettier.objectWrap: "preserve"` keeps manually multiline objects multiline, for example in `.vscode/settings.json`.
