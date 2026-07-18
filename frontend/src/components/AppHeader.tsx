import { useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import recipesImage from '../../img/recipes.png';

type Section = 'general' | 'recipes' | 'admin';

interface AppHeaderProps {
  activeSection: Section;
  onSelectSection: (section: Section) => void;
  onGoToRecipeOverview: () => void;
  recipeSearchQuery: string;
  onRecipeSearchChange: (value: string) => void;
  onRequestCreateRecipe: () => void;
}

export function AppHeader({
  activeSection,
  onSelectSection,
  onGoToRecipeOverview,
  recipeSearchQuery,
  onRecipeSearchChange,
  onRequestCreateRecipe,
}: AppHeaderProps) {
  const { user, logout, mayManageUsers, isAuthenticated, mayEditRecipes } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  function selectSection(section: Section) {
    onSelectSection(section);
    setMenuOpen(false);
  }

  const showRecipeActions = isAuthenticated && activeSection === 'recipes';

  return (
    <header className="hero">
      <div className="hero-main">
        <div className="hero-heading">
          <button
            type="button"
            className="hero-overview-link"
            onClick={onGoToRecipeOverview}
            aria-label="Zur Rezeptübersicht"
          >
            <img
              src={recipesImage}
              alt="Rezeptsammlung"
              className="hero-recipes-image"
              loading="eager"
            />
          </button>
          <div>
            <p className="eyebrow">Familienrezepte</p>
            <h1>
              <button
                type="button"
                className="hero-overview-link hero-overview-title"
                onClick={onGoToRecipeOverview}
              >
                Unsere Rezeptsammlung
              </button>
            </h1>
          </div>
        </div>
        <p>Rezepte verwalten, Bilder testen und Benutzerrechte steuern.</p>

        <div className="header-toolbar">
          <div className="header-menu-wrapper">
            <button
              type="button"
              className="hamburger-button"
              aria-label="Navigation öffnen"
              aria-expanded={menuOpen}
              aria-controls="main-header-menu"
              onClick={() => setMenuOpen((current) => !current)}
            >
              <span />
              <span />
              <span />
            </button>

            {menuOpen && (
              <div id="main-header-menu" className="header-menu" role="menu">
                {isAuthenticated && (
                  <button
                    type="button"
                    role="menuitem"
                    className={activeSection === 'recipes' ? 'active' : ''}
                    onClick={() => selectSection('recipes')}
                  >
                    Rezepte
                  </button>
                )}
                <button
                  type="button"
                  role="menuitem"
                  className={activeSection === 'general' ? 'active' : ''}
                  onClick={() => selectSection('general')}
                >
                  System
                </button>
                {mayManageUsers && (
                  <button
                    type="button"
                    role="menuitem"
                    className={activeSection === 'admin' ? 'active' : ''}
                    onClick={() => selectSection('admin')}
                  >
                    Admin
                  </button>
                )}
              </div>
            )}
          </div>

          {showRecipeActions && (
            <div className="recipe-toolbar-actions">
              {mayEditRecipes && (
                <button
                  type="button"
                  className="recipe-create-button"
                  onClick={onRequestCreateRecipe}
                >
                  +
                </button>
              )}
              <input
                type="search"
                aria-label="Rezepte durchsuchen"
                value={recipeSearchQuery}
                onChange={(event) => onRecipeSearchChange(event.target.value)}
                placeholder="Name, Zutat oder Schlagwort"
              />
            </div>
          )}
        </div>
      </div>

      {user && (
        <div className="header-user">
          <div>
            <strong>
              {user.first_name} {user.last_name}
            </strong>
            <div className="muted">@{user.username}</div>
          </div>
          <span className="auth-token">
            {user.is_super_admin ? 'Super-Admin' : mayManageUsers ? 'Administrator' : 'Benutzer'}
          </span>
          <button type="button" className="button-secondary" onClick={logout}>
            Abmelden
          </button>
        </div>
      )}
    </header>
  );
}
