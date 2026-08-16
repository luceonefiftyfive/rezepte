import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { RecipeEditor } from './RecipeEditor';

const AVAILABLE_GROUPS = [
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
];

const SINGLE_AVAILABLE_GROUP = [
  {
    id: 'recipes',
    name: 'Rezepte',
    description: null,
    created_at: '2026-07-17T10:00:00Z',
    updated_at: '2026-07-17T10:00:00Z',
  },
];

describe('RecipeEditor', () => {
  async function selectGroup(user: ReturnType<typeof userEvent.setup>, groupName: string) {
    await user.click(
      screen.getByRole('button', { name: /Rezeptbuecher auswählen|Rezeptbücher auswählen/i }),
    );
    await user.click(screen.getByLabelText(groupName));
    await user.click(screen.getByRole('button', { name: 'Auswahl übernehmen' }));
  }

  it('enables header save only after the draft changes', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(
      <RecipeEditor
        onSave={vi.fn().mockResolvedValue(undefined)}
        onCancel={onCancel}
        availableGroups={SINGLE_AVAILABLE_GROUP}
      />,
    );

    const saveButton = screen.getByRole('button', { name: 'Speichern' });
    expect(saveButton).toBeDisabled();

    await user.type(screen.getByLabelText('Name'), 'Kartoffelsuppe');
    expect(saveButton).toBeEnabled();

    await user.click(screen.getByRole('button', { name: 'Abbrechen' }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('submits structured ingredients and instruction steps', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<RecipeEditor onSave={onSave} availableGroups={AVAILABLE_GROUPS} />);

    await selectGroup(user, 'Rezepte');

    await user.type(screen.getByLabelText('Name'), 'Kartoffelsuppe');
    await user.type(screen.getByLabelText('Quelle'), '  Omas Kochbuch  ');
    await user.clear(screen.getByLabelText('Menge'));
    await user.type(screen.getByLabelText('Menge'), '6');
    await user.type(screen.getByLabelText('Abschnitt 1'), 'Für die Suppe');
    await user.type(screen.getByLabelText('Menge der Zutat'), '1000');
    await user.selectOptions(screen.getByLabelText('Einheit'), 'g');
    await user.type(screen.getByLabelText('Zutat'), 'Kartoffeln');
    await user.type(screen.getByLabelText('Vorbereitung'), 'geschält');
    await user.type(screen.getByLabelText('Zubereitungsschritt 1'), 'Kartoffeln kochen.');

    await user.click(screen.getByRole('button', { name: 'Zutat hinzufügen' }));
    const ingredientInputs = screen.getAllByLabelText('Zutat');
    await user.type(ingredientInputs[1], 'Salz');
    const unitInputs = screen.getAllByLabelText('Einheit');
    await user.selectOptions(unitInputs[1], 'as_needed');

    await user.click(screen.getByRole('button', { name: 'Schritt hinzufügen' }));
    await user.type(screen.getByLabelText('Zubereitungsschritt 2'), 'Suppe pürieren.');
    await user.click(screen.getByRole('button', { name: 'Speichern' }));

    expect(onSave).toHaveBeenCalledOnce();
    const payload = onSave.mock.calls[0][0];
    expect(payload.title).toBe('Kartoffelsuppe');
    expect(payload.source).toBe('Omas Kochbuch');
    expect(payload.yield).toEqual({ amount: '6', unit: 'Portionen' });
    expect(payload.ingredient_sections[0].name).toBe('Für die Suppe');
    expect(payload.ingredient_sections[0].ingredients).toHaveLength(2);
    expect(payload.ingredient_sections[0].ingredients[0]).toMatchObject({
      name: 'Kartoffeln',
      amount: '1000',
      unit: 'g',
      preparation: 'geschält',
    });
    expect(payload.ingredient_sections[0].ingredients[1]).toMatchObject({
      name: 'Salz',
      unit: 'as_needed',
    });
    expect(payload.instructions.map((step: { text: string }) => step.text)).toEqual([
      'Kartoffeln kochen.',
      'Suppe pürieren.',
    ]);
  });

  it('auto-selects and shows the single available group', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<RecipeEditor onSave={onSave} availableGroups={SINGLE_AVAILABLE_GROUP} />);

    expect(screen.getByText('Rezepte')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', {
        name: /Rezeptbuecher auswählen|Rezeptbücher auswählen/i,
      }),
    ).not.toBeInTheDocument();

    await user.type(screen.getByLabelText('Name'), 'Nudeln');
    await user.type(screen.getByLabelText('Zutat'), 'Pasta');
    await user.type(screen.getByLabelText('Zubereitungsschritt 1'), 'Kochen.');
    await user.click(screen.getByRole('button', { name: 'Speichern' }));

    expect(onSave).toHaveBeenCalledOnce();
    const payload = onSave.mock.calls[0][0];
    expect(payload.group_ids).toEqual(['recipes']);
  });

  it('requires at least one selected group in multi-select mode', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<RecipeEditor onSave={onSave} availableGroups={AVAILABLE_GROUPS} />);

    await user.type(screen.getByLabelText('Name'), 'Nudeln');
    await user.type(screen.getByLabelText('Zutat'), 'Pasta');
    await user.type(screen.getByLabelText('Zubereitungsschritt 1'), 'Kochen.');
    await user.click(screen.getByRole('button', { name: 'Speichern' }));

    expect(onSave).not.toHaveBeenCalled();
    expect(screen.getByText('Bitte mindestens ein Rezeptbuch auswählen.')).toBeInTheDocument();
  });

  it('supports custom units and removing rows', async () => {
    const user = userEvent.setup();
    render(
      <RecipeEditor
        onSave={vi.fn().mockResolvedValue(undefined)}
        availableGroups={AVAILABLE_GROUPS}
      />,
    );
    await user.selectOptions(screen.getByLabelText('Einheit'), 'custom');
    expect(screen.getByLabelText('Eigene Einheit')).toBeInTheDocument();
    await user.click(screen.getByLabelText('Zutat löschen'));
    expect(screen.queryByLabelText('Zutat')).not.toBeInTheDocument();
  });

  it('imports ingredients and instructions from markdown lists', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<RecipeEditor onSave={onSave} availableGroups={AVAILABLE_GROUPS} />);

    await selectGroup(user, 'Rezepte');

    await user.type(screen.getByLabelText('Name'), 'Salbei-Spaghetti');
    await user.click(screen.getByRole('button', { name: 'Markdown importieren' }));
    await user.type(
      screen.getByLabelText('Zutaten (Markdown)'),
      `pro Person:\n- 125 g Nudeln\n- 1 Knoblauchzehe\n- viel frischer Salbei`,
    );

    await user.type(
      screen.getByLabelText('Arbeitsschritte (Markdown)'),
      `- Salbeiblätter waschen und trocknen\n- Spaghetti kochen`,
    );
    await user.click(screen.getByRole('button', { name: 'Beides importieren' }));

    await user.click(screen.getByRole('button', { name: 'Speichern' }));

    expect(onSave).toHaveBeenCalledOnce();
    const payload = onSave.mock.calls[0][0];
    expect(payload.ingredient_sections[0].name).toBe('pro Person');
    expect(payload.ingredient_sections[0].ingredients).toHaveLength(3);
    expect(payload.ingredient_sections[0].ingredients[0]).toMatchObject({
      name: 'Nudeln',
      amount: '125',
      unit: 'g',
    });
    expect(payload.ingredient_sections[0].ingredients[1]).toMatchObject({
      name: 'Knoblauch',
      amount: '1',
      unit: 'clove',
    });
    expect(payload.ingredient_sections[0].ingredients[2]).toMatchObject({
      name: 'viel frischer Salbei',
      amount: null,
      unit: 'as_needed',
    });
    expect(payload.instructions.map((step: { text: string }) => step.text)).toEqual([
      'Salbeiblätter waschen und trocknen',
      'Spaghetti kochen',
    ]);
  });

  it('parses compact quantities and german unit phrases from markdown imports', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<RecipeEditor onSave={onSave} availableGroups={AVAILABLE_GROUPS} />);

    await selectGroup(user, 'Rezepte');

    await user.type(screen.getByLabelText('Name'), 'Kraeuterreis');
    await user.click(screen.getByRole('button', { name: 'Markdown importieren' }));
    await user.type(
      screen.getByLabelText('Zutaten (Markdown)'),
      `- 1 große Prise Safranfäden\n- 300g Basmatireis\n- 3 Kardamomkapseln\n- 1 mehligkochende Kartoffel (relativ groß)\n- 1 großes Bund gemischte Kräuter\n- 20g Pistazienkerne\n- 6EL Joghurt\n- Meersalz, schwarzer Pfeffer\``,
    );
    await user.click(screen.getByRole('button', { name: 'Nur Zutaten importieren' }));
    await user.type(screen.getByLabelText('Zubereitungsschritt 1'), 'Alles mischen.');
    await user.click(screen.getByRole('button', { name: 'Speichern' }));

    expect(onSave).toHaveBeenCalledOnce();
    const payload = onSave.mock.calls[0][0];
    expect(payload.ingredient_sections[0].ingredients).toHaveLength(8);
    expect(payload.ingredient_sections[0].ingredients[0]).toMatchObject({
      name: 'Safranfäden',
      amount: '1',
      unit: 'pinch',
    });
    expect(payload.ingredient_sections[0].ingredients[1]).toMatchObject({
      name: 'Basmatireis',
      amount: '300',
      unit: 'g',
    });
    expect(payload.ingredient_sections[0].ingredients[2]).toMatchObject({
      name: 'Kardamomkapseln',
      amount: '3',
      unit: 'piece',
    });
    expect(payload.ingredient_sections[0].ingredients[4]).toMatchObject({
      name: 'gemischte Kräuter',
      amount: '1',
      unit: 'bunch',
    });
    expect(payload.ingredient_sections[0].ingredients[6]).toMatchObject({
      name: 'Joghurt',
      amount: '6',
      unit: 'tbsp',
    });
    expect(payload.ingredient_sections[0].ingredients[7]).toMatchObject({
      name: 'Meersalz, schwarzer Pfeffer',
      amount: null,
      unit: 'as_needed',
    });
  });
});
