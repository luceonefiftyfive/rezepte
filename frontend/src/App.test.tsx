import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./api/client', () => ({ apiFetch: vi.fn() }));
vi.mock('./features/general/GeneralSection', () => ({
  GeneralSection: () => <div>General Section</div>,
}));

import App from './App';
import { AuthProvider } from './auth/AuthContext';
import { apiFetch } from './api/client';

const mockedApiFetch = vi.mocked(apiFetch);

describe('App login flow', () => {
  beforeEach(() => {
    mockedApiFetch.mockReset();
    window.localStorage.clear();
  });

  it('loads recipes immediately after login without requiring a manual reload', async () => {
    const user = {
      id: 'user-1',
      username: 'anna',
      first_name: 'Anna',
      last_name: 'Beispiel',
      email: 'anna@example.com',
      email_verified: true,
      is_active: true,
      is_super_admin: false,
      groups: [{ group_id: 'family', role: 'author' as const }],
    };
    const groups = [
      {
        id: 'family',
        name: 'Familie',
        description: null,
        created_at: '2026-07-18T08:00:00Z',
        updated_at: '2026-07-18T08:00:00Z',
      },
    ];
    const recipes = [
      {
        id: 'recipe-1',
        title: 'Brot',
        description: 'Einfach',
        group_ids: ['family'],
        tags: ['Backen'],
        time: { preparation_minutes: 10, cooking_minutes: 40, resting_minutes: 60 },
        yield: { amount: '1', unit: 'Laib' },
        ingredient_sections: [],
        instructions: [],
        remarks: null,
        created_at: '2026-07-18T08:00:00Z',
        updated_at: '2026-07-18T08:00:00Z',
        version: 1,
      },
    ];

    mockedApiFetch.mockImplementation(async (path) => {
      if (path === '/auth/login') {
        return { access_token: 'token-1', token_type: 'bearer', user };
      }
      if (path === '/auth/me') {
        return user;
      }
      if (path === '/groups' || path === '/groups?manageable_only=true') {
        return groups;
      }
      if (path === '/recipes?sort=created_desc') {
        return recipes;
      }

      throw new Error(`Unexpected path: ${path}`);
    });

    render(
      <AuthProvider>
        <App />
      </AuthProvider>,
    );

    fireEvent.change(screen.getByLabelText('Benutzername'), { target: { value: 'anna' } });
    fireEvent.change(screen.getByLabelText('Passwort'), { target: { value: 'geheim' } });
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }));

    await waitFor(() => expect(screen.getByText('Brot')).toBeInTheDocument());

    expect(mockedApiFetch).toHaveBeenCalledWith(
      '/auth/login',
      expect.objectContaining({ method: 'POST' }),
      null,
    );
    expect(mockedApiFetch).toHaveBeenCalledWith('/auth/me', {}, 'token-1');
    expect(mockedApiFetch).toHaveBeenCalledWith('/groups', {}, 'token-1');
    expect(mockedApiFetch).toHaveBeenCalledWith('/groups?manageable_only=true', {}, 'token-1');
    expect(mockedApiFetch).toHaveBeenCalledWith('/recipes?sort=created_desc', {}, 'token-1');
  });
});
