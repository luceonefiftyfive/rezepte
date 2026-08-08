# Recipe Web Application – User Navigation and UX Specification

## 1. Overview

The application is a responsive web application for managing recipes.

It is implemented using **Vite and React** and must provide a consistent user experience on:

- Desktop computers
- Tablets
- Smartphones

The specification and technical documentation are written in English.

**The application's user interface must be in German.**

This includes all:

- Page titles
- Navigation items
- Buttons
- Labels
- Form fields
- Dialogs
- Confirmation messages
- Validation messages
- Error messages
- Notifications

After successful authentication, the user is taken directly to the recipe overview.

Recipes are the primary focus of the application. Administrative functions must not be permanently visible in the main interface and are accessible exclusively through the hamburger menu.

---

# 2. Main User Flow

```text id="m2krzy"
Anmeldung
   │
   ▼
Meine Rezepte
   │
   ├── Rezepte suchen
   │
   ├── Neues Rezept
   │
   └── Rezept auswählen
            │
            ▼
       Rezeptdetails
            │
            ├── Zurück
            │     └── Meine Rezepte
            │
            └── Bearbeiten
                    │
                    ▼
             Rezept bearbeiten
                    │
                    ├── Speichern
                    │     └── Rezeptdetails
                    │
                    └── Abbrechen
                          └── Rezeptdetails
```

---

# 3. Login

When the application is opened without an authenticated session, the login page is displayed.

The UI should use German labels, for example:

```text id="21aqvv"
Anmeldung

Benutzername
[________________________]

Passwort
[________________________]

[ Anmelden ]
```

After successful authentication, the user is redirected to:

```text id="5j9n2e"
/recipes
```

---

# 4. Recipe Overview

The recipe overview is the main page of the application.

It displays all recipes available to the authenticated user.

Each recipe may contain summary information such as:

- Title
- Image
- Short description
- Preparation time
- Category or tags

The main actions are:

- Search recipes
- Create a new recipe
- Open an existing recipe

The corresponding German UI labels should be:

```text id="trn5mx"
Suche
Neues Rezept
```

Example desktop layout:

```text id="cpw5q1"
┌─────────────────────────────────────────────────────────────┐
│ ☰   Rezeptesammlung               🔍 Suche  + Neues Rezept │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌───────────┐  ┌───────────┐  ┌───────────┐                 │
│ │   Bild    │  │   Bild    │  │   Bild    │                 │
│ │           │  │           │  │           │                 │
│ │ Lasagne   │  │ Gulasch   │  │ Risotto   │                 │
│ └───────────┘  └───────────┘  └───────────┘                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

On smartphones, the same functions should be available, but the layout should adapt to the smaller screen.

Example:

```text id="45sb96"
┌────────────────────────┐
│ ☰  Rezeptesammlung    │
│                        │
│ 🔍 Suche        + Neu  │
├────────────────────────┤
│                        │
│ ┌────────────────────┐ │
│ │        Bild        │ │
│ │      Lasagne       │ │
│ └────────────────────┘ │
│                        │
│ ┌────────────────────┐ │
│ │        Bild        │ │
│ │       Gulasch      │ │
│ └────────────────────┘ │
│                        │
└────────────────────────┘
```

The functionality and navigation model must remain consistent across screen sizes.

---

# 5. Recipe Details

Selecting a recipe opens its detail page.

The page may contain:

- Title
- Image
- Description
- Ingredients
- Quantities
- Preparation instructions
- Preparation time
- Number of servings
- Categories or tags

The German actions are:

```text id="v49gfn"
Zurück
Bearbeiten
```

`Zurück` returns to the recipe overview.

Where possible, the previous state of the recipe overview should be preserved, including:

- Search query
- Filters
- Scroll position

`Bearbeiten` opens the recipe editor for the current recipe.

---

# 6. Create Recipe

Selecting `Neues Rezept` from the recipe overview opens the recipe editor in create mode.

Route:

```text id="9gg2i3"
/recipes/new
```

The editor should use German labels.

Example actions:

```text id="2rt33j"
Speichern
Abbrechen
```

After saving the new recipe, the application navigates to the detail page of the newly created recipe.

```text id="3k4ffw"
Neues Rezept
      │
      ▼
Rezept bearbeiten
      │
      ├── Speichern
      │      │
      │      ▼
      │ Rezeptdetails
      │
      └── Abbrechen
             │
             ▼
       Meine Rezepte
```

---

# 7. Edit Recipe

An existing recipe can be edited from its detail page.

Route:

```text id="u7udvp"
/recipes/:id/edit
```

The edit form should reuse the same form components used when creating a recipe.

Actions:

```text id="dvz2x7"
Speichern
Abbrechen
```

After saving, the application returns to the recipe detail page.

`Abbrechen` discards the changes and returns to the recipe detail page.

---

# 8. Hamburger Menu

The hamburger menu is the central location for secondary and administrative functions.

It must be available on both desktop and mobile devices.

For a regular user, the menu should appear as:

```text id="vnwbmm"
☰

Meine Rezepte
Mein Profil

Abmelden
```

For a user with the appropriate administrative permissions:

```text id="18h1ha"
☰

Meine Rezepte
Mein Profil

Verwaltung
  ├── Personen
  ├── Gruppen
  └── Datenverwaltung

Abmelden
```

`Verwaltung` must only be visible if the authenticated user has at least one administrative permission.

Individual administration menu entries should also be displayed according to the user's permissions.

Administrative functionality must not be directly exposed in the normal recipe navigation.

---

# 9. My Profile

Every authenticated user can manage their own account information.

Route:

```text id="xywm5n"
/profile
```

The German page title should be:

```text id="y9xcmc"
Mein Profil
```

Possible account information includes:

- Display name
- Username
- Email address
- Password

Possible German UI labels:

```text id="0prz0y"
Anzeigename
Benutzername
E-Mail-Adresse
Passwort ändern

Speichern
Abbrechen
```

Security-sensitive changes, such as changing the password, should require appropriate verification, for example the current password or re-authentication.

---

# 10. User Administration

Users with the required permissions can manage other users.

User administration is accessible exclusively through:

```text id="jxfvns"
☰ → Verwaltung → Personen
```

Route:

```text id="3wz6f0"
/admin/users
```

The German UI should use the term:

```text id="8ugkqr"
Personen
```

Available operations include:

- View users
- Search users
- Create users
- View user details
- Edit users
- Delete users

Example UI:

```text id="b0ok5j"
Personen

🔍 Person suchen                         + Neue Person

------------------------------------------------------
Name              Benutzername       Gruppen
------------------------------------------------------
Anna Müller       amueller           Familie
Peter Schmidt     pschmidt           Familie, Freunde
Max Mustermann    mmuster            Freunde
------------------------------------------------------
```

Selecting a person opens the corresponding detail page.

Example:

```text id="o8pf65"
Person

Anna Müller

Benutzername:  amueller
E-Mail:        anna@example.de
Status:        Aktiv

Gruppen:
✓ Familie
□ Freunde
✓ Kochgruppe

[ Bearbeiten ]              [ Löschen ]
```

Users may belong to one or more groups.

---

# 11. Group Administration

Users with the required permissions can manage groups.

Group administration is accessible through:

```text id="vrgwjf"
☰ → Verwaltung → Gruppen
```

Route:

```text id="cwm32f"
/admin/groups
```

Available operations include:

- View groups
- Create groups
- View group details
- Edit groups
- Delete groups

Example:

```text id="52h0q1"
Gruppen

🔍 Gruppe suchen                         + Neue Gruppe

--------------------------------------------------
Gruppe                              Mitglieder
--------------------------------------------------
Familie                                  5
Freunde                                   8
Kochgruppe                                4
--------------------------------------------------
```

A group may contain:

- Name
- Description
- Members
- Permissions or roles

Group membership should be visible both from the user administration and from the group administration.

---

# 12. Data Management

Administrative data operations are accessible exclusively through:

```text id="9c2igf"
☰ → Verwaltung → Datenverwaltung
```

Route:

```text id="w16rff"
/admin/data
```

The page contains three main functions:

```text id="smf3de"
Rezepte exportieren
Rezepte importieren
Datenbank löschen
```

Example:

```text id="tjmc1i"
Datenverwaltung


Export
──────────────────────────────────────────

Rezepte und zugehörige Daten exportieren.

[ Rezepte exportieren ]


Import
──────────────────────────────────────────

Rezepte aus einer Exportdatei importieren.

[ Datei auswählen ]     [ Importieren ]


Gefahrenbereich
──────────────────────────────────────────

ACHTUNG:
Mit dieser Funktion können alle Daten der
Anwendung unwiderruflich gelöscht werden.

[ Datenbank vollständig löschen ]
```

---

# 13. Recipe Export

Users with the required permission can export recipe data.

The export should contain all information required to restore or transfer recipes.

Depending on the application's data model, this may include:

- Recipes
- Ingredients
- Preparation steps
- Categories
- Tags
- Images or image references

The German action is:

```text id="5rfs1r"
Rezepte exportieren
```

The export format should be defined separately.

---

# 14. Recipe Import

Users with the required permission can import recipes from an export file.

Before starting the import, the application must validate the selected file.

The UI may provide the following German options:

```text id="5z64vf"
Nur neue Rezepte hinzufügen

Vorhandene Rezepte aktualisieren

Vorhandene Rezepte vollständig ersetzen
```

Operations that overwrite existing data must require additional confirmation.

After the import, the application should provide a German summary, for example:

```text id="u4v2nz"
Import abgeschlossen

42 Rezepte importiert
7 Rezepte aktualisiert
2 Rezepte übersprungen
0 Fehler
```

---

# 15. Delete Database

Deleting the complete database is a highly destructive administrative operation.

It must only be available to users with the specific permission required for this operation.

The user interface must display a prominent warning.

Example:

```text id="lv1z3g"
Datenbank vollständig löschen

Diese Aktion löscht unwiderruflich alle Daten
der Anwendung, einschließlich:

• Rezepte
• Personen
• Gruppen
• weiterer gespeicherter Anwendungsdaten

Dieser Vorgang kann nicht rückgängig gemacht werden.

[ Abbrechen ]                         [ Weiter ]
```

A second explicit confirmation should be required.

For example:

```text id="zy3ou3"
Bestätigung erforderlich

Geben Sie zur Bestätigung

LÖSCHEN

in das folgende Feld ein:

[____________________________]

[ Abbrechen ]        [ Endgültig löschen ]
```

A complete export or backup should preferably be offered before executing the deletion.

---

# 16. Permissions

Permissions must be enforced independently of the user interface.

Hiding a button, menu entry, or React component is not sufficient security.

Every protected operation must also be authorized by the backend.

A possible permission model is:

```text id="qsc2bi"
recipes.read
recipes.create
recipes.edit
recipes.delete

recipes.export
recipes.import

users.read
users.create
users.edit
users.delete

groups.read
groups.create
groups.edit
groups.delete

database.delete
```

The exact permission model can be refined during implementation.

For example, a user may have permission to administer persons without having permission to delete the complete database.

---

# 17. Routing

A possible route structure is:

```text id="rt6r9g"
/login

/recipes
/recipes/new
/recipes/:id
/recipes/:id/edit

/profile

/admin/users
/admin/users/new
/admin/users/:id
/admin/users/:id/edit

/admin/groups
/admin/groups/new
/admin/groups/:id
/admin/groups/:id/edit

/admin/data
```

Administrative routes must be protected according to the authenticated user's permissions.

The technical route names remain in English even though the visible UI is German.

---

# 18. Responsive Design

The application must use the same conceptual navigation on desktop, tablet, and smartphone devices.

The layout adapts to the available screen size, but the functionality and terminology remain consistent.

### Desktop example

```text id="fzqxrn"
┌─────────────────────────────────────────────────────────────┐
│ ☰   Meine Rezepte                 🔍 Suche  + Neues Rezept │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                       Rezeptübersicht                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Smartphone example

```text id="zy60le"
┌────────────────────────┐
│ ☰  Meine Rezepte       │
│                        │
│ 🔍 Suche        + Neu  │
├────────────────────────┤
│                        │
│ ┌────────────────────┐ │
│ │        Bild        │ │
│ │      Lasagne       │ │
│ └────────────────────┘ │
│                        │
│ ┌────────────────────┐ │
│ │        Bild        │ │
│ │       Gulasch      │ │
│ └────────────────────┘ │
│                        │
└────────────────────────┘
```

Administrative functions remain accessible exclusively through the hamburger menu on all screen sizes.

---

# 19. Overall Navigation Structure

```text id="mmdfpz"
Application
│
├── Anmeldung
│
└── Authenticated Area
     │
     ├── Meine Rezepte
     │    │
     │    ├── Suche
     │    ├── Rezept anzeigen
     │    ├── Neues Rezept
     │    └── Rezept bearbeiten
     │
     └── ☰ Hamburger Menu
          │
          ├── Meine Rezepte
          │
          ├── Mein Profil
          │    └── Anmeldedaten bearbeiten
          │
          ├── Verwaltung
          │    │
          │    ├── Personen
          │    │    ├── Anzeigen
          │    │    ├── Anlegen
          │    │    ├── Bearbeiten
          │    │    └── Löschen
          │    │
          │    ├── Gruppen
          │    │    ├── Anzeigen
          │    │    ├── Anlegen
          │    │    ├── Bearbeiten
          │    │    └── Löschen
          │    │
          │    └── Datenverwaltung
          │         ├── Rezepte exportieren
          │         ├── Rezepte importieren
          │         └── Datenbank löschen
          │
          └── Abmelden
```

---

# 20. UX Principles

The application should follow these general principles:

- Recipes are the primary focus of the application.
- The application UI is in German.
- Technical documentation, source code identifiers, routes, and permission names may use English.
- Common recipe actions should be immediately accessible.
- Administrative functionality must not clutter the normal recipe workflow.
- Administration is accessible exclusively through the hamburger menu.
- Administrative menu entries are displayed according to the user's permissions.
- UI visibility is not a substitute for backend authorization.
- Desktop and mobile versions use the same conceptual navigation.
- Create and edit workflows should use consistent interaction patterns.
- Destructive operations require explicit confirmation.
- Highly destructive operations require an additional confirmation step.
- Browser and device back-navigation should behave predictably.
- Returning to the recipe overview should preserve search, filter, and scroll state whenever possible.
