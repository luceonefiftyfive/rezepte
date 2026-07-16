import { useState } from 'react';
import { useAuth } from './auth/AuthContext';
import { AppHeader } from './components/AppHeader';
import { LoginPanel } from './components/LoginPanel';
import { AdminSection } from './features/admin/AdminSection';
import { GeneralSection } from './features/general/GeneralSection';
import { RecipeSection } from './features/recipes/RecipeSection';

type Section = 'general' | 'recipes' | 'admin';

export default function App() {
  const { isAuthenticated, mayManageUsers } = useAuth();
  const [section, setSection] = useState<Section>('general');

  const visibleSection: Section =
    section === 'admin' && !mayManageUsers
      ? 'general'
      : section === 'recipes' && !isAuthenticated
        ? 'general'
        : section;

  return (
    <main className="page">
      <AppHeader />

      <nav className="main-nav" aria-label="Hauptnavigation">
        <button
          className={visibleSection === 'general' ? 'active' : ''}
          onClick={() => setSection('general')}
        >
          System
        </button>
        {isAuthenticated && (
          <button
            className={visibleSection === 'recipes' ? 'active' : ''}
            onClick={() => setSection('recipes')}
          >
            Rezepte
          </button>
        )}
        {mayManageUsers && (
          <button
            className={visibleSection === 'admin' ? 'active' : ''}
            onClick={() => setSection('admin')}
          >
            Admin
          </button>
        )}
      </nav>

      {!isAuthenticated && <LoginPanel />}
      {visibleSection === 'general' && <GeneralSection />}
      {visibleSection === 'recipes' && isAuthenticated && <RecipeSection />}
      {visibleSection === 'admin' && mayManageUsers && <AdminSection />}
    </main>
  );
}
