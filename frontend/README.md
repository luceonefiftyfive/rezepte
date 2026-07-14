# Familienrezepte – Frontend

React-/Vite-Frontend für das aktuelle FastAPI-Backend.

## Enthaltene Funktionen

- Anmeldung über `/auth/login` und Laden des aktuellen Benutzers über `/auth/me`
- Speicherung des Zugriffstokens im Browser
- Systemstatus für API, MongoDB und S3
- Tests für angemeldete Benutzer, Administratoren und Super-Administratoren
- Rezept anlegen, auflisten, durchsuchen und löschen
- Bild-Upload zum vorhandenen S3-Testendpunkt
- Benutzer anlegen, Gruppenrollen verwalten, Super-Admin-Status setzen und Benutzer deaktivieren
- Deutsche Benutzeroberfläche

## Entwicklung

```bash
npm install
npm run dev
```

Vite leitet `/api` standardmäßig an `http://localhost:8000` weiter und entfernt dabei das Präfix `/api`.
Ein anderes Backend kann gesetzt werden mit:

```bash
VITE_DEV_API_TARGET=http://backend:8000 npm run dev
```

## Produktions-Build

```bash
npm run build
```

Das Ergebnis liegt anschließend in `dist/`.

## Konfiguration

Siehe `.env.example`:

```env
VITE_API_BASE_URL=/api
VITE_DEV_API_TARGET=http://localhost:8000
```

In einer produktiven Umgebung sollte der Reverse Proxy `/api/*` an FastAPI weiterleiten.

## Recipe editor V2

The recipe editor supports structured ingredient sections, ingredients with normalized units, custom units, preparation notes, optional ingredients, ordered instruction steps, yield, preparation/cooking/resting times, tags, recipe-book IDs, editing and deletion.

Run tests and build:

```bash
npm install
npm test
npm run build
```
