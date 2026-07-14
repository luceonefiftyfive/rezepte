import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { RecipeEditor } from './RecipeEditor';

describe('RecipeEditor', () => {
  it('submits structured ingredients and instruction steps', async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<RecipeEditor onSave={onSave} />);

    await user.type(screen.getByLabelText('Name'), 'Kartoffelsuppe');
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
    await user.click(screen.getByRole('button', { name: 'Rezept speichern' }));

    expect(onSave).toHaveBeenCalledOnce();
    const payload = onSave.mock.calls[0][0];
    expect(payload.title).toBe('Kartoffelsuppe');
    expect(payload.yield).toEqual({ amount: '6', unit: 'Portionen' });
    expect(payload.ingredient_sections[0].name).toBe('Für die Suppe');
    expect(payload.ingredient_sections[0].ingredients).toHaveLength(2);
    expect(payload.ingredient_sections[0].ingredients[0]).toMatchObject({ name: 'Kartoffeln', amount: '1000', unit: 'g', preparation: 'geschält' });
    expect(payload.ingredient_sections[0].ingredients[1]).toMatchObject({ name: 'Salz', unit: 'as_needed' });
    expect(payload.instructions.map((step: { text: string }) => step.text)).toEqual(['Kartoffeln kochen.', 'Suppe pürieren.']);
  });

  it('supports custom units and removing rows', async () => {
    const user = userEvent.setup();
    render(<RecipeEditor onSave={vi.fn().mockResolvedValue(undefined)} />);
    await user.selectOptions(screen.getByLabelText('Einheit'), 'custom');
    expect(screen.getByLabelText('Eigene Einheit')).toBeInTheDocument();
    await user.click(screen.getByLabelText('Zutat löschen'));
    expect(screen.queryByLabelText('Zutat')).not.toBeInTheDocument();
  });
});
