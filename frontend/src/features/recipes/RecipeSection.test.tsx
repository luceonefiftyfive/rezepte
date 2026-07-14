import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RecipeSection } from './RecipeSection';

vi.mock('../../auth/AuthContext', () => ({ useAuth: () => ({ token: 'test-token' }) }));
vi.mock('../../api/client', () => ({ apiFetch: vi.fn() }));

import { apiFetch } from '../../api/client';
const mockedApiFetch = vi.mocked(apiFetch);

describe('RecipeSection', () => {
  beforeEach(() => { mockedApiFetch.mockReset(); });

  it('renders ingredient and instruction summaries returned by the backend', async () => {
    mockedApiFetch.mockResolvedValueOnce([{
      id: 'recipe-1', title: 'Brot', description: 'Einfach', group_ids: [], tags: ['Backen'],
      time: { preparation_minutes: 10, cooking_minutes: 40, resting_minutes: 60 },
      yield: { amount: '1', unit: 'Laib' },
      ingredient_sections: [{ id: 'main', name: null, ingredients: [{ name: 'Mehl', amount: '500', unit: 'g', optional: false, scaling: 'linear' }] }],
      instructions: [{ id: 'step-1', text: 'Teig kneten.' }], remarks: null,
      created_at: '2026-07-12T12:00:00Z', updated_at: '2026-07-12T12:00:00Z', version: 1,
    }]);
    render(<RecipeSection />);
    await waitFor(() => expect(screen.getByText('Brot')).toBeInTheDocument());
    expect(screen.getByText(/Zutaten:/).parentElement).toHaveTextContent('Mehl');
    expect(screen.getByText(/Zubereitung:/).parentElement).toHaveTextContent('1 Schritte');
  });
});
