import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RecipeSection } from './RecipeSection';

vi.mock('../../auth/AuthContext', () => ({ useAuth: () => ({ token: 'test-token' }) }));
vi.mock('../../api/client', () => ({ apiFetch: vi.fn() }));

import { apiFetch } from '../../api/client';
const mockedApiFetch = vi.mocked(apiFetch);

describe('RecipeSection', () => {
  beforeEach(() => {
    mockedApiFetch.mockReset();
  });

  it('renders ingredient and instruction summaries returned by the backend', async () => {
    mockedApiFetch.mockResolvedValueOnce([
      {
        id: 'recipe-1',
        title: 'Brot',
        description: 'Einfach',
        group_ids: [],
        tags: ['Backen'],
        time: { preparation_minutes: 10, cooking_minutes: 40, resting_minutes: 60 },
        yield: { amount: '1', unit: 'Laib' },
        ingredient_sections: [
          {
            id: 'main',
            name: null,
            ingredients: [
              { name: 'Mehl', amount: '500', unit: 'g', optional: false, scaling: 'linear' },
            ],
          },
        ],
        instructions: [{ id: 'step-1', text: 'Teig kneten.' }],
        remarks: null,
        created_at: '2026-07-12T12:00:00Z',
        updated_at: '2026-07-12T12:00:00Z',
        version: 1,
      },
    ]);
    render(<RecipeSection />);
    await waitFor(() => expect(screen.getByText('Brot')).toBeInTheDocument());
    expect(screen.getByText('Mehl')).toBeInTheDocument();
    expect(screen.getByText('1 Schritte')).toBeInTheDocument();
  });

  it('shows recipe details when the list item is viewed', async () => {
    mockedApiFetch.mockResolvedValueOnce([
      {
        id: 'recipe-1',
        title: 'Brot',
        description: 'Einfach',
        group_ids: ['family'],
        tags: ['Backen'],
        time: { preparation_minutes: 10, cooking_minutes: 40, resting_minutes: 60 },
        yield: { amount: '1', unit: 'Laib' },
        ingredient_sections: [
          {
            id: 'main',
            name: 'Für den Teig',
            ingredients: [
              { name: 'Mehl', amount: '500', unit: 'g', optional: false, scaling: 'linear' },
            ],
          },
        ],
        instructions: [{ id: 'step-1', text: 'Teig kneten.' }],
        remarks: 'Frisch servieren.',
        created_at: '2026-07-12T12:00:00Z',
        updated_at: '2026-07-12T12:00:00Z',
        version: 1,
      },
    ]);

    render(<RecipeSection />);
    await waitFor(() => expect(screen.getByText('Brot')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Anzeigen/i }));

    const detailSection = screen.getByRole('heading', { name: 'Rezept ansehen' }).closest('.card');
    expect(detailSection).toBeInTheDocument();
    expect(detailSection).toHaveTextContent('Einfach');
    expect(detailSection).toHaveTextContent('Mehl');
    expect(detailSection).toHaveTextContent('Teig kneten.');
    expect(detailSection).toHaveTextContent('Frisch servieren.');
  });
});
