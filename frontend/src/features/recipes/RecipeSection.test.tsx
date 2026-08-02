import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RecipeSection } from './RecipeSection';
import QRCode from 'qrcode';

vi.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({ token: 'test-token', mayEditRecipes: true }),
}));
vi.mock('../../api/client', () => ({ apiFetch: vi.fn() }));
vi.mock('qrcode', () => ({
  default: {
    toString: vi.fn().mockResolvedValue('<svg xmlns="http://www.w3.org/2000/svg"></svg>'),
  },
}));

import { apiFetch } from '../../api/client';
const mockedApiFetch = vi.mocked(apiFetch);
const mockedQrCodeToString = vi.mocked(QRCode.toString);

describe('RecipeSection', () => {
  function mockGroups() {
    mockedApiFetch.mockResolvedValueOnce([
      {
        id: 'recipes',
        name: 'Rezepte',
        description: null,
        created_at: '2026-07-17T10:00:00Z',
        updated_at: '2026-07-17T10:00:00Z',
      },
      {
        id: 'family',
        name: 'Familie',
        description: null,
        created_at: '2026-07-17T10:00:00Z',
        updated_at: '2026-07-17T10:00:00Z',
      },
    ]);
    mockedApiFetch.mockResolvedValueOnce([
      {
        id: 'recipes',
        name: 'Rezepte',
        description: null,
        created_at: '2026-07-17T10:00:00Z',
        updated_at: '2026-07-17T10:00:00Z',
      },
      {
        id: 'family',
        name: 'Familie',
        description: null,
        created_at: '2026-07-17T10:00:00Z',
        updated_at: '2026-07-17T10:00:00Z',
      },
    ]);
  }

  beforeEach(() => {
    mockedApiFetch.mockReset();
    mockedQrCodeToString.mockImplementation(() => new Promise<string>(() => {}));
    window.history.replaceState({}, '', '/');
  });

  it('renders recipes returned by the backend in the overview list', async () => {
    mockGroups();
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
    expect(screen.getByRole('button', { name: /Rezept anzeigen Brot/i })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Neues Rezept' })).not.toBeInTheDocument();
  });

  it('shows recipe details when the list item is viewed', async () => {
    mockGroups();
    mockedApiFetch.mockResolvedValueOnce([
      {
        id: 'recipe-1',
        title: 'Brot',
        description: 'Einfach',
        source: 'https://example.com/brot',
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

    fireEvent.click(screen.getByRole('button', { name: /Rezept anzeigen Brot/i }));

    const detailSection = screen.getByRole('heading', { name: 'Rezept ansehen' }).closest('.card');
    expect(detailSection).toBeInTheDocument();
    expect(detailSection).toHaveTextContent('Einfach');
    expect(detailSection).toHaveTextContent('https://example.com/brot');
    expect(detailSection).toHaveTextContent('Mehl');
    expect(detailSection).toHaveTextContent('Teig kneten.');
    expect(detailSection).toHaveTextContent('Frisch servieren.');
  });

  it('requests recipes again when the sort order changes', async () => {
    mockGroups();
    mockedApiFetch
      .mockResolvedValueOnce([
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
          created_at: '2026-07-12T12:00:00Z',
          updated_at: '2026-07-12T12:00:00Z',
          version: 1,
        },
      ])
      .mockResolvedValueOnce([
        {
          id: 'recipe-2',
          title: 'Apfelmus',
          description: 'Alphabetisch',
          group_ids: ['family'],
          tags: ['Dessert'],
          time: { preparation_minutes: 5, cooking_minutes: 15, resting_minutes: 0 },
          yield: { amount: '2', unit: 'Gläser' },
          ingredient_sections: [],
          instructions: [],
          remarks: null,
          created_at: '2026-07-13T12:00:00Z',
          updated_at: '2026-07-13T12:00:00Z',
          version: 1,
        },
      ]);

    render(<RecipeSection />);
    await waitFor(() => expect(screen.getByText('Brot')).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText('Rezeptsortierung'), {
      target: { value: 'title_asc' },
    });

    await waitFor(() => expect(screen.getByText('Apfelmus')).toBeInTheDocument());
    expect(mockedApiFetch).toHaveBeenCalledWith(
      '/recipes?sort=title_asc&group_ids=recipes%2Cfamily',
      {},
      'test-token',
    );
  });

  it('refreshes recipe overview after saving an edited recipe', async () => {
    mockGroups();
    mockedApiFetch
      .mockResolvedValueOnce([
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
          created_at: '2026-07-12T12:00:00Z',
          updated_at: '2026-07-12T12:00:00Z',
          version: 1,
        },
      ])
      .mockResolvedValueOnce({
        id: 'recipe-1',
        title: 'Brot verbessert',
        description: 'Einfach',
        group_ids: ['family'],
        tags: ['Backen'],
        time: { preparation_minutes: 10, cooking_minutes: 40, resting_minutes: 60 },
        yield: { amount: '1', unit: 'Laib' },
        ingredient_sections: [],
        instructions: [],
        remarks: null,
        created_at: '2026-07-12T12:00:00Z',
        updated_at: '2026-07-13T12:00:00Z',
        version: 2,
      })
      .mockResolvedValueOnce([
        {
          id: 'recipe-1',
          title: 'Brot verbessert',
          description: 'Einfach',
          group_ids: ['family'],
          tags: ['Backen'],
          time: { preparation_minutes: 10, cooking_minutes: 40, resting_minutes: 60 },
          yield: { amount: '1', unit: 'Laib' },
          ingredient_sections: [],
          instructions: [],
          remarks: null,
          created_at: '2026-07-12T12:00:00Z',
          updated_at: '2026-07-13T12:00:00Z',
          version: 2,
        },
      ]);

    render(<RecipeSection />);
    await waitFor(() => expect(screen.getByText('Brot')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Rezept anzeigen Brot/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Bearbeiten' }));
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Brot verbessert' } });
    fireEvent.click(screen.getByRole('button', { name: 'Änderungen speichern' }));

    await waitFor(() => expect(screen.getByText('Brot verbessert')).toBeInTheDocument());

    expect(mockedApiFetch).toHaveBeenCalledWith(
      '/recipes/recipe-1',
      expect.objectContaining({ method: 'PUT' }),
      'test-token',
    );
    expect(mockedApiFetch).toHaveBeenCalledWith(
      '/recipes?sort=created_desc&group_ids=recipes%2Cfamily',
      {},
      'test-token',
    );
  });

  it('renders recipe and step images when signed URLs are available', async () => {
    mockGroups();
    mockedApiFetch
      .mockResolvedValueOnce([
        {
          id: 'recipe-1',
          title: 'Brot',
          description: 'Mit Foto',
          recipe_image_key: 'recipes/recipe-1/cover/cover.jpg',
          group_ids: ['family'],
          tags: ['Backen'],
          time: { preparation_minutes: 10, cooking_minutes: 40, resting_minutes: 60 },
          yield: { amount: '1', unit: 'Laib' },
          ingredient_sections: [],
          instructions: [
            {
              id: 'step-1',
              text: 'Teig kneten.',
              image_key: 'recipes/recipe-1/steps/step-1/step.jpg',
            },
          ],
          remarks: null,
          created_at: '2026-07-12T12:00:00Z',
          updated_at: '2026-07-12T12:00:00Z',
          version: 1,
        },
      ])
      .mockResolvedValueOnce({
        ok: true,
        key: 'recipes/recipe-1/cover/cover.jpg',
        view_url: 'https://nuc01/api/recipes/images/recipes/recipe-1/cover/cover.jpg',
        expires_in: 3600,
      })
      .mockResolvedValueOnce({
        ok: true,
        key: 'recipes/recipe-1/steps/step-1/step.jpg',
        view_url: 'https://nuc01/api/recipes/images/recipes/recipe-1/steps/step-1/step.jpg',
        expires_in: 3600,
      });

    render(<RecipeSection />);
    await waitFor(() => expect(screen.getByText('Brot')).toBeInTheDocument());

    await waitFor(() => {
      const previewImage = screen.getByAltText('Vorschaubild Brot') as HTMLImageElement;
      expect(previewImage.src).toContain('/api/recipes/images/recipes/recipe-1/cover/cover.jpg');
    });

    fireEvent.click(screen.getByRole('button', { name: /Rezept anzeigen Brot/i }));

    await waitFor(() => {
      const recipeImage = screen.getByAltText('Rezeptbild Brot') as HTMLImageElement;
      expect(recipeImage.src).toContain('/api/recipes/images/recipes/recipe-1/cover/cover.jpg');
    });

    const stepImage = screen.getByAltText('Schrittbild Brot') as HTMLImageElement;
    expect(stepImage.src).toContain('/api/recipes/images/recipes/recipe-1/steps/step-1/step.jpg');
  });

  it('returns to overview when overview request version changes', async () => {
    mockGroups();
    mockedApiFetch.mockResolvedValueOnce([
      {
        id: 'recipe-1',
        title: 'Brot',
        description: 'Einfach',
        group_ids: [],
        tags: ['Backen'],
        time: { preparation_minutes: 10, cooking_minutes: 40, resting_minutes: 60 },
        yield: { amount: '1', unit: 'Laib' },
        ingredient_sections: [],
        instructions: [],
        remarks: null,
        created_at: '2026-07-12T12:00:00Z',
        updated_at: '2026-07-12T12:00:00Z',
        version: 1,
      },
    ]);

    const { rerender } = render(
      <RecipeSection createRequestVersion={1} overviewRequestVersion={0} />,
    );

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Neues Rezept' })).toBeInTheDocument(),
    );

    rerender(<RecipeSection createRequestVersion={1} overviewRequestVersion={1} />);

    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: 'Neues Rezept' })).not.toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Rezept anzeigen Brot/i })).toBeInTheDocument();
    });
  });

  it('falls back to visible groups in editor when manageable groups are empty', async () => {
    mockedApiFetch.mockResolvedValueOnce([
      {
        id: 'recipes',
        name: 'Rezepte',
        description: null,
        created_at: '2026-07-17T10:00:00Z',
        updated_at: '2026-07-17T10:00:00Z',
      },
      {
        id: 'family',
        name: 'Familie',
        description: null,
        created_at: '2026-07-17T10:00:00Z',
        updated_at: '2026-07-17T10:00:00Z',
      },
    ]);
    mockedApiFetch.mockResolvedValueOnce([]);
    mockedApiFetch.mockResolvedValueOnce([]);

    render(<RecipeSection createRequestVersion={1} />);

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Neues Rezept' })).toBeInTheDocument(),
    );

    expect(
      screen.getByRole('button', {
        name: /Rezeptbuecher auswählen \(0\)|Rezeptbücher auswählen \(0\)/i,
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText('Keine verfügbaren Rezeptbücher.')).not.toBeInTheDocument();
  });

  it('loads recipes even when no groups are returned', async () => {
    mockedApiFetch.mockResolvedValueOnce([]);
    mockedApiFetch.mockResolvedValueOnce([]);
    mockedApiFetch.mockResolvedValueOnce([
      {
        id: 'recipe-1',
        title: 'Brot',
        description: 'Einfach',
        group_ids: ['legacy-group'],
        tags: ['Backen'],
        time: { preparation_minutes: 10, cooking_minutes: 40, resting_minutes: 60 },
        yield: { amount: '1', unit: 'Laib' },
        ingredient_sections: [],
        instructions: [],
        remarks: null,
        created_at: '2026-07-12T12:00:00Z',
        updated_at: '2026-07-12T12:00:00Z',
        version: 1,
      },
    ]);

    render(<RecipeSection />);

    await waitFor(() => expect(screen.getByText('Brot')).toBeInTheDocument());
  });

  it('opens a recipe detail automatically when recipe id is present in URL', async () => {
    mockGroups();
    window.history.replaceState({}, '', '/?recipe=recipe-1');
    mockedApiFetch.mockResolvedValueOnce([
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
        created_at: '2026-07-12T12:00:00Z',
        updated_at: '2026-07-12T12:00:00Z',
        version: 1,
      },
    ]);

    render(<RecipeSection />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Rezept ansehen' })).toBeInTheDocument();
      expect(screen.getByText('Einfach')).toBeInTheDocument();
    });
  });

  it('copies a shareable recipe link from detail view', async () => {
    mockGroups();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(window.navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });
    mockedApiFetch.mockResolvedValueOnce([
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
        created_at: '2026-07-12T12:00:00Z',
        updated_at: '2026-07-12T12:00:00Z',
        version: 1,
      },
    ]);

    render(<RecipeSection />);
    await waitFor(() => expect(screen.getByText('Brot')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Rezept anzeigen Brot/i }));
    fireEvent.click(screen.getByRole('button', { name: 'Link kopieren' }));

    await waitFor(() => expect(writeText).toHaveBeenCalled());
    expect(writeText.mock.calls[0]?.[0]).toContain('?recipe=recipe-1');
    expect(
      screen.getByText('Rezept-Link wurde in die Zwischenablage kopiert.'),
    ).toBeInTheDocument();
  });

  it('opens print dialog from recipe detail view for PDF export', async () => {
    mockGroups();
    const printSpy = vi.spyOn(window, 'print').mockImplementation(() => undefined);
    mockedQrCodeToString.mockImplementationOnce(
      async () => '<svg xmlns="http://www.w3.org/2000/svg"></svg>',
    );
    window.history.replaceState({}, '', '/?foo=bar');
    mockedApiFetch.mockResolvedValueOnce([
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
        created_at: '2026-07-12T12:00:00Z',
        updated_at: '2026-07-12T12:00:00Z',
        version: 1,
      },
    ]);

    render(<RecipeSection />);
    await waitFor(() => expect(screen.getByText('Brot')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /Rezept anzeigen Brot/i }));
    const printableLink = document.querySelector('.recipe-print-link a');
    expect(printableLink).not.toBeNull();
    expect(printableLink).toHaveAttribute(
      'href',
      expect.stringContaining('?foo=bar&recipe=recipe-1'),
    );
    await waitFor(() =>
      expect(screen.getByAltText('QR-Code fuer Rezept-Link')).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByRole('button', { name: 'Drucken / PDF' }));

    expect(printSpy).toHaveBeenCalledTimes(1);
    printSpy.mockRestore();
  });
});
