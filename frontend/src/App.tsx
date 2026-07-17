import { useEffect, useRef, useState } from 'react';
import { useAuth } from './auth/AuthContext';
import { AppHeader } from './components/AppHeader';
import { LoginPanel } from './components/LoginPanel';
import { AdminSection } from './features/admin/AdminSection';
import { GeneralSection } from './features/general/GeneralSection';
import { RecipeSection } from './features/recipes/RecipeSection';

type Section = 'general' | 'recipes' | 'admin';

export default function App() {
  const { isAuthenticated, mayManageUsers } = useAuth();
  const [section, setSection] = useState<Section>(isAuthenticated ? 'recipes' : 'general');
  const [recipeSearchQuery, setRecipeSearchQuery] = useState('');
  const [recipeCreateRequestVersion, setRecipeCreateRequestVersion] = useState(0);
  const [recipeOverviewRequestVersion, setRecipeOverviewRequestVersion] = useState(0);
  const wasAuthenticated = useRef(isAuthenticated);

  useEffect(() => {
    if (!wasAuthenticated.current && isAuthenticated) {
      setSection('recipes');
    }
    if (wasAuthenticated.current && !isAuthenticated && section === 'recipes') {
      setSection('general');
    }
    wasAuthenticated.current = isAuthenticated;
  }, [isAuthenticated, section]);

  const visibleSection: Section =
    section === 'admin' && !mayManageUsers
      ? 'general'
      : section === 'recipes' && !isAuthenticated
        ? 'general'
        : section;

  function requestRecipeCreate() {
    setRecipeCreateRequestVersion((current) => current + 1);
  }

  function handleSelectSection(nextSection: Section) {
    if (nextSection === 'recipes') {
      setRecipeOverviewRequestVersion((current) => current + 1);
    }
    setSection(nextSection);
  }

  function handleGoToRecipeOverview() {
    if (!isAuthenticated) {
      setSection('general');
      return;
    }

    setRecipeOverviewRequestVersion((current) => current + 1);
    setSection('recipes');
  }

  return (
    <main className="page">
      <AppHeader
        activeSection={visibleSection}
        onSelectSection={handleSelectSection}
        onGoToRecipeOverview={handleGoToRecipeOverview}
        recipeSearchQuery={recipeSearchQuery}
        onRecipeSearchChange={setRecipeSearchQuery}
        onRequestCreateRecipe={requestRecipeCreate}
      />

      {!isAuthenticated && <LoginPanel />}
      {visibleSection === 'general' && <GeneralSection />}
      {visibleSection === 'recipes' && isAuthenticated && (
        <RecipeSection
          searchQuery={recipeSearchQuery}
          createRequestVersion={recipeCreateRequestVersion}
          overviewRequestVersion={recipeOverviewRequestVersion}
        />
      )}
      {visibleSection === 'admin' && mayManageUsers && <AdminSection />}
    </main>
  );
}
