import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockUseAuth = vi.fn();

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('../api/client', () => ({
  apiFetch: vi.fn(),
}));

import { AppHeader } from './AppHeader';

describe('AppHeader', () => {
  beforeEach(() => {
    mockUseAuth.mockReset();
    localStorage.clear();
  });

  it('shows the search field when the search toggle is pressed', async () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: 'user-1',
        username: 'anna',
        first_name: 'Anna',
        last_name: 'Beispiel',
        email: 'anna@example.com',
        email_verified: true,
        is_active: true,
        is_super_admin: false,
      },
      logout: vi.fn(),
      mayManageUsers: false,
      isAuthenticated: true,
      mayEditRecipes: true,
    });

    render(
      <AppHeader
        activeSection="recipes"
        onSelectSection={() => undefined}
        onGoToRecipeOverview={() => undefined}
        recipeSearchQuery=""
        onRecipeSearchChange={() => undefined}
        onRequestCreateRecipe={() => undefined}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /suche/i }));

    const searchField = screen.getByLabelText('Rezepte durchsuchen');
    expect(searchField).toBeInTheDocument();
    expect(searchField).toHaveFocus();
  });

  it('stores up to ten recent search terms for later selection', async () => {
    mockUseAuth.mockReturnValue({
      mayManageUsers: false,
      isAuthenticated: true,
      mayEditRecipes: true,
    });
    const onRecipeSearchChange = vi.fn();

    render(
      <AppHeader
        activeSection="recipes"
        onSelectSection={() => undefined}
        onGoToRecipeOverview={() => undefined}
        recipeSearchQuery="Kartoffelsuppe"
        onRecipeSearchChange={onRecipeSearchChange}
        onRequestCreateRecipe={() => undefined}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /suche/i }));
    fireEvent.keyDown(screen.getByLabelText('Rezepte durchsuchen'), { key: 'Enter' });

    expect(localStorage.getItem('recipe-search-history')).toBe('["Kartoffelsuppe"]');
    expect(document.querySelector('datalist option')).toHaveAttribute('value', 'Kartoffelsuppe');
  });
});
