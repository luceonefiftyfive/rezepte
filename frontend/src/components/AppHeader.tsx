import { useEffect, useState } from 'react';
import { apiFetch } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import type { SystemVersionResponse } from '../types';
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
  const { mayManageUsers, isAuthenticated, mayEditRecipes } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [systemVersion, setSystemVersion] = useState<SystemVersionResponse | null>(null);
  const [versionLoading, setVersionLoading] = useState(false);
  const [versionError, setVersionError] = useState(false);

  async function loadSystemVersion(): Promise<void> {
    setVersionLoading(true);
    setVersionError(false);
    try {
      const data = await apiFetch<SystemVersionResponse>('/system/version');
      setSystemVersion(data);
    } catch {
      setVersionError(true);
    } finally {
      setVersionLoading(false);
    }
  }

  useEffect(() => {
    void loadSystemVersion();
  }, []);

  function selectSection(section: Section) {
    onSelectSection(section);
    setMenuOpen(false);
  }

  const showRecipeActions = isAuthenticated && activeSection === 'recipes';
  const [searchOpen, setSearchOpen] = useState(false);

  return (
    <header className="hero">
      <div className="hero-main">
        <div className="header-toolbar">
          <div className="header-left-actions">
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
                  <div className="menu-version-box" role="presentation">
                    <div className="menu-version-label">Version</div>
                    <div className="menu-version-value">
                      {versionLoading
                        ? 'Lade ...'
                        : systemVersion
                          ? `${systemVersion.version} (${systemVersion.git_hash})`
                          : 'Unbekannt'}
                    </div>
                    {versionError && (
                      <div className="menu-version-error">Konnte nicht geladen werden.</div>
                    )}
                    <button
                      type="button"
                      className="menu-version-refresh"
                      onClick={() => void loadSystemVersion()}
                    >
                      Aktualisieren
                    </button>
                  </div>
                </div>
              )}
            </div>

            {showRecipeActions && mayEditRecipes && (
              <button
                type="button"
                className="recipe-create-button"
                onClick={onRequestCreateRecipe}
                aria-label="Neues Rezept erstellen"
              >
                +
              </button>
            )}

            {showRecipeActions && (
              <button
                type="button"
                className="search-toggle"
                aria-label="Suche"
                onClick={() => setSearchOpen((current) => !current)}
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="11" cy="11" r="8" />
                  <path d="m21 21-4.35-4.35" />
                </svg>
              </button>
            )}
          </div>

          {showRecipeActions && searchOpen && (
            <input
              type="search"
              className="header-search-input"
              aria-label="Rezepte durchsuchen"
              value={recipeSearchQuery}
              onChange={(event) => onRecipeSearchChange(event.target.value)}
              placeholder="Name, Zutat oder Schlagwort"
            />
          )}

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
              <h1>
                <button
                  type="button"
                  className="hero-overview-link hero-overview-title"
                  onClick={onGoToRecipeOverview}
                >
                  Rezeptesammlung
                </button>
              </h1>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
