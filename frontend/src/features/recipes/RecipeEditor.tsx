import { ChangeEvent, FormEvent, useEffect, useRef, useState } from 'react';
import type {
  Group,
  ImageUploadResponse,
  IngredientSection,
  Recipe,
  RecipeIngredient,
  RecipePayload,
  Unit,
} from '../../types';

const units: Array<{ value: Unit; label: string }> = [
  { value: 'g', label: 'g' },
  { value: 'kg', label: 'kg' },
  { value: 'ml', label: 'ml' },
  { value: 'l', label: 'l' },
  { value: 'tsp', label: 'TL' },
  { value: 'tbsp', label: 'EL' },
  { value: 'piece', label: 'Stück' },
  { value: 'pinch', label: 'Prise' },
  { value: 'bunch', label: 'Bund' },
  { value: 'clove', label: 'Zehe' },
  { value: 'slice', label: 'Scheibe' },
  { value: 'cup', label: 'Tasse' },
  { value: 'as_needed', label: 'nach Bedarf' },
  { value: 'custom', label: 'eigene Einheit' },
];

const unitAliases: Record<string, Unit> = {
  g: 'g',
  gramm: 'g',
  gr: 'g',
  kg: 'kg',
  ml: 'ml',
  l: 'l',
  tl: 'tsp',
  tsp: 'tsp',
  el: 'tbsp',
  tbsp: 'tbsp',
  stueck: 'piece',
  stck: 'piece',
  st: 'piece',
  prise: 'pinch',
  bund: 'bunch',
  zehe: 'clove',
  zehen: 'clove',
  scheibe: 'slice',
  scheiben: 'slice',
  tasse: 'cup',
  tassen: 'cup',
};

function normalizeUnitToken(value: string): string {
  return value
    .trim()
    .toLocaleLowerCase('de')
    .replace(/ä/g, 'ae')
    .replace(/ö/g, 'oe')
    .replace(/ü/g, 'ue')
    .replace(/ß/g, 'ss')
    .replace(/\./g, '')
    .replace(/[^a-z]/g, '');
}

function parseFractionAmount(value: string): string {
  const normalized = value.replace(',', '.');
  if (!normalized.includes('/')) {
    return normalized;
  }
  const [numeratorRaw, denominatorRaw] = normalized.split('/');
  const numerator = Number(numeratorRaw);
  const denominator = Number(denominatorRaw);
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator === 0) {
    return normalized;
  }
  return (numerator / denominator).toString();
}

function cleanIngredientName(value: string): string {
  return value.replace(/[\s`;,.:]+$/g, '').trim();
}

function splitAmountPrefix(line: string): { amount: string | null; rest: string } {
  const match = line.match(/^(\d+(?:[.,]\d+)?(?:\s*\/\s*\d+(?:[.,]\d+)?)?)(.*)$/);
  if (!match) {
    return { amount: null, rest: line.trim() };
  }
  return {
    amount: parseFractionAmount(match[1].replace(/\s+/g, '')),
    rest: match[2].trim(),
  };
}

function findUnitAliasInTokens(tokens: string[]): { index: number; unit: Unit } | null {
  for (let i = 0; i < Math.min(tokens.length, 3); i += 1) {
    const aliasUnit = unitAliases[normalizeUnitToken(tokens[i])];
    if (aliasUnit) {
      return { index: i, unit: aliasUnit };
    }
  }
  return null;
}

function parseMarkdownLines(markdown: string): string[] {
  return markdown
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => /^([-*+]\s+|\d+[.)]\s+)/.test(line))
    .map((line) =>
      line
        .replace(/^[-*+]\s+/, '')
        .replace(/^\d+[.)]\s+/, '')
        .replace(/^\[[ xX]\]\s+/, '')
        .trim(),
    )
    .filter((line) => line.length > 0);
}

function parseIngredientMarkdown(markdown: string): {
  sectionName: string | null;
  ingredients: RecipeIngredient[];
} {
  const lines = markdown
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  const sectionName =
    lines
      .find((line) => !/^([-*+]\s+|\d+[.)]\s+)/.test(line) && line.endsWith(':'))
      ?.replace(/:$/, '')
      .trim() ?? null;
  const bulletLines = parseMarkdownLines(markdown);

  const ingredients = bulletLines.map((line) => {
    const split = splitAmountPrefix(line);
    let text = split.rest;
    const amount = split.amount;
    let unit: Unit = 'as_needed';
    let custom_unit: string | null = null;

    const tokens = text.split(/\s+/).filter(Boolean);
    const unitMatch = findUnitAliasInTokens(tokens);
    if (unitMatch) {
      unit = unitMatch.unit;
      text = tokens
        .slice(unitMatch.index + 1)
        .join(' ')
        .trim();
    }

    if (amount && unit === 'as_needed') {
      const zeheMatch = text.match(/^([A-Za-zÄÖÜäöüß-]+?)(zehe|zehen)$/i);
      if (zeheMatch) {
        unit = 'clove';
        text = zeheMatch[1].trim();
      } else {
        unit = 'piece';
      }
    }

    if (!text) {
      text = line;
    }

    text = cleanIngredientName(text);

    return {
      ...newIngredient(),
      amount,
      unit,
      custom_unit,
      name: text,
    };
  });

  return {
    sectionName,
    ingredients,
  };
}

function parseInstructionMarkdown(markdown: string): Array<{ id: string; text: string }> {
  return parseMarkdownLines(markdown).map((text) => ({ id: crypto.randomUUID(), text }));
}

function newIngredient(): RecipeIngredient {
  return {
    name: '',
    amount: null,
    unit: 'g',
    custom_unit: null,
    preparation: null,
    remarks: null,
    optional: false,
    scaling: 'linear',
  };
}
function newSection(): IngredientSection {
  return { id: crypto.randomUUID(), name: null, ingredients: [newIngredient()] };
}
function emptyPayload(): RecipePayload {
  return {
    title: '',
    description: null,
    source: null,
    recipe_image_key: null,
    group_ids: [],
    tags: [],
    time: { preparation_minutes: null, cooking_minutes: null, resting_minutes: null },
    yield: { amount: '4', unit: 'Portionen' },
    ingredient_sections: [newSection()],
    instructions: [{ id: crypto.randomUUID(), text: '' }],
    remarks: null,
  };
}

function draftSnapshot(form: RecipePayload, tags: string, selectedGroups: string[]): string {
  return JSON.stringify({ form, tags, selectedGroups: [...selectedGroups].sort() });
}

export function RecipeEditor({
  recipe,
  availableGroups,
  forceSingleGroupId,
  busy = false,
  onSave,
  onCancel,
  onUploadRecipeImage,
  onUploadInstructionImage,
}: {
  recipe?: Recipe | null;
  availableGroups: Group[];
  forceSingleGroupId?: string | null;
  busy?: boolean;
  onSave: (payload: RecipePayload, version?: number) => Promise<void>;
  onCancel?: () => void;
  onUploadRecipeImage?: (recipeId: string, file: File) => Promise<ImageUploadResponse>;
  onUploadInstructionImage?: (
    recipeId: string,
    stepId: string,
    file: File,
  ) => Promise<ImageUploadResponse>;
}) {
  const resolvedSingleGroupId =
    forceSingleGroupId ?? (availableGroups.length === 1 ? availableGroups[0].id : null);
  const [form, setForm] = useState<RecipePayload>(() => recipe ?? emptyPayload());
  const [tags, setTags] = useState(recipe?.tags.join(', ') ?? '');
  const [selectedGroups, setSelectedGroups] = useState<string[]>(recipe?.group_ids ?? []);
  const [ingredientMarkdown, setIngredientMarkdown] = useState('');
  const [instructionMarkdown, setInstructionMarkdown] = useState('');
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);
  const [isGroupDialogOpen, setIsGroupDialogOpen] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadStatus, setUploadStatus] = useState('');
  const [validationError, setValidationError] = useState('');
  const [recipeImageUrl, setRecipeImageUrl] = useState<string | null>(null);
  const [stepImageUrls, setStepImageUrls] = useState<Record<string, string>>({});
  const initialDraftRef = useRef('');

  useEffect(() => {
    const initialForm = recipe ?? emptyPayload();
    const initialTags = recipe?.tags.join(', ') ?? '';
    const initialGroups = resolvedSingleGroupId
      ? [resolvedSingleGroupId]
      : (recipe?.group_ids ?? []);
    setForm(initialForm);
    setTags(initialTags);
    setSelectedGroups(initialGroups);
    initialDraftRef.current = draftSnapshot(initialForm, initialTags, initialGroups);
    setIngredientMarkdown('');
    setInstructionMarkdown('');
    setIsGroupDialogOpen(false);
    setUploadError('');
    setUploadStatus('');
    setValidationError('');
    setRecipeImageUrl(null);
    setStepImageUrls({});
  }, [recipe, resolvedSingleGroupId]);

  const hasChanges = draftSnapshot(form, tags, selectedGroups) !== initialDraftRef.current;

  useEffect(() => {
    if (resolvedSingleGroupId) {
      setSelectedGroups([resolvedSingleGroupId]);
      return;
    }
    setSelectedGroups((current) =>
      current.filter((groupId) => availableGroups.some((group) => group.id === groupId)),
    );
  }, [availableGroups, resolvedSingleGroupId]);

  function toggleSelectedGroup(groupId: string) {
    setSelectedGroups((current) => {
      if (current.includes(groupId)) {
        if (current.length === 1) {
          setValidationError('Bitte mindestens ein Rezeptbuch auswählen.');
          return current;
        }
        return current.filter((id) => id !== groupId);
      }
      setValidationError('');
      return [...current, groupId];
    });
  }

  function selectAllGroups() {
    setSelectedGroups(availableGroups.map((group) => group.id));
    setValidationError('');
  }

  function updateSection(sectionIndex: number, section: IngredientSection) {
    setForm((current) => ({
      ...current,
      ingredient_sections: current.ingredient_sections.map((value, index) =>
        index === sectionIndex ? section : value,
      ),
    }));
  }
  function updateIngredient(
    sectionIndex: number,
    ingredientIndex: number,
    patch: Partial<RecipeIngredient>,
  ) {
    const section = form.ingredient_sections[sectionIndex];
    updateSection(sectionIndex, {
      ...section,
      ingredients: section.ingredients.map((value, index) =>
        index === ingredientIndex ? { ...value, ...patch } : value,
      ),
    });
  }
  function importIngredientsFromMarkdown() {
    const parsed = parseIngredientMarkdown(ingredientMarkdown);
    if (parsed.ingredients.length === 0) {
      return;
    }
    setForm((current) => ({
      ...current,
      ingredient_sections: [
        {
          ...newSection(),
          name: parsed.sectionName,
          ingredients: parsed.ingredients,
        },
      ],
    }));
  }
  function importFromMarkdown() {
    importIngredientsFromMarkdown();
    importInstructionsFromMarkdown();
    setIsImportDialogOpen(false);
  }
  function importInstructionsFromMarkdown() {
    const parsed = parseInstructionMarkdown(instructionMarkdown);
    if (parsed.length === 0) {
      return;
    }
    setForm((current) => ({
      ...current,
      instructions: parsed,
    }));
  }

  async function handleRecipeImageUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!recipe?.id || !onUploadRecipeImage) {
      setUploadError('Bild-Upload ist erst nach dem ersten Speichern verfügbar.');
      event.target.value = '';
      return;
    }

    setUploadError('');
    setUploadStatus('');
    try {
      const uploaded = await onUploadRecipeImage(recipe.id, file);
      setForm((current) => ({ ...current, recipe_image_key: uploaded.key }));
      setRecipeImageUrl(uploaded.view_url ?? null);
      setUploadStatus('Rezeptbild wurde hochgeladen.');
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      event.target.value = '';
    }
  }

  async function handleInstructionImageUpload(
    stepId: string,
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!recipe?.id || !onUploadInstructionImage) {
      setUploadError('Bild-Upload ist erst nach dem ersten Speichern verfügbar.');
      event.target.value = '';
      return;
    }

    setUploadError('');
    setUploadStatus('');
    try {
      const uploaded = await onUploadInstructionImage(recipe.id, stepId, file);
      setForm((current) => ({
        ...current,
        instructions: current.instructions.map((step) =>
          step.id === stepId ? { ...step, image_key: uploaded.key } : step,
        ),
      }));
      if (uploaded.view_url) {
        setStepImageUrls((current) => ({ ...current, [stepId]: uploaded.view_url as string }));
      }
      setUploadStatus('Schrittbild wurde hochgeladen.');
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      event.target.value = '';
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const groupIds =
      resolvedSingleGroupId && selectedGroups.length === 0
        ? [resolvedSingleGroupId]
        : selectedGroups;
    if (groupIds.length === 0) {
      setValidationError('Bitte mindestens ein Rezeptbuch auswählen.');
      return;
    }
    setValidationError('');

    const payload: RecipePayload = {
      ...form,
      title: form.title.trim(),
      description: form.description?.trim() || null,
      source: form.source?.trim() || null,
      remarks: form.remarks?.trim() || null,
      tags: tags
        .split(',')
        .map((value) => value.trim())
        .filter(Boolean),
      group_ids: groupIds,
      ingredient_sections: form.ingredient_sections.map((section) => ({
        ...section,
        name: section.name?.trim() || null,
        ingredients: section.ingredients
          .filter((ingredient) => ingredient.name.trim())
          .map((ingredient) => ({
            ...ingredient,
            name: ingredient.name.trim(),
            custom_unit: ingredient.custom_unit?.trim() || null,
            preparation: ingredient.preparation?.trim() || null,
            remarks: ingredient.remarks?.trim() || null,
          })),
      })),
      instructions: form.instructions
        .filter((step) => step.text.trim())
        .map((step) => ({ ...step, text: step.text.trim(), image_key: step.image_key ?? null })),
    };
    await onSave(payload, recipe?.version);
    if (!recipe) {
      setForm(emptyPayload());
      setTags('');
      setSelectedGroups(resolvedSingleGroupId ? [resolvedSingleGroupId] : []);
    }
  }

  return (
    <form className="card form recipe-editor" onSubmit={submit}>
      <div className="section-heading compact">
        <h3>{recipe ? 'Rezept bearbeiten' : 'Neues Rezept'}</h3>
        <div className="button-row">
          <button type="submit" disabled={busy || !form.title.trim() || !hasChanges}>
            {busy ? 'Speichern …' : 'Speichern'}
          </button>
          {onCancel && (
            <button type="button" className="button-secondary" onClick={onCancel}>
              Abbrechen
            </button>
          )}
          <button
            type="button"
            className="button-secondary"
            onClick={() => setIsImportDialogOpen(true)}
          >
            Markdown importieren
          </button>
        </div>
      </div>

      {isImportDialogOpen && (
        <div className="import-dialog-backdrop" role="presentation">
          <div
            className="import-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="import-dialog-title"
          >
            <div className="section-heading compact">
              <h4 id="import-dialog-title">Markdown-Import</h4>
              <button
                type="button"
                className="button-secondary"
                onClick={() => setIsImportDialogOpen(false)}
              >
                Schließen
              </button>
            </div>
            <label>
              Zutaten als Markdown
              <span className="label-help">
                Listen mit <code>-</code> oder <code>1.</code>; z. B. auch <code>300g</code> oder{' '}
                <code>6EL</code>.
              </span>
              <textarea
                aria-label="Zutaten (Markdown)"
                rows={8}
                value={ingredientMarkdown}
                onChange={(e) => setIngredientMarkdown(e.target.value)}
              />
            </label>
            <label>
              Arbeitsschritte als Markdown
              <span className="label-help">
                Listen mit <code>-</code> oder nummeriert.
              </span>
              <textarea
                aria-label="Arbeitsschritte (Markdown)"
                rows={8}
                value={instructionMarkdown}
                onChange={(e) => setInstructionMarkdown(e.target.value)}
              />
            </label>
            <div className="button-row">
              <button
                type="button"
                className="button-secondary"
                onClick={importIngredientsFromMarkdown}
              >
                Nur Zutaten importieren
              </button>
              <button
                type="button"
                className="button-secondary"
                onClick={importInstructionsFromMarkdown}
              >
                Nur Schritte importieren
              </button>
              <button type="button" onClick={importFromMarkdown}>
                Beides importieren
              </button>
            </div>
          </div>
        </div>
      )}
      {isGroupDialogOpen && !resolvedSingleGroupId && availableGroups.length > 0 && (
        <div className="import-dialog-backdrop" role="presentation">
          <div
            className="import-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="group-dialog-title"
          >
            <div className="section-heading compact">
              <h4 id="group-dialog-title">Rezeptbücher auswählen</h4>
              <button
                type="button"
                className="button-secondary"
                onClick={() => setIsGroupDialogOpen(false)}
              >
                Schließen
              </button>
            </div>
            <p className="muted">Mehrfachauswahl für Erstellung und Bearbeitung.</p>
            <div className="button-row">
              <button type="button" className="button-secondary" onClick={selectAllGroups}>
                Alle auswählen
              </button>
            </div>
            <div className="group-picker-list">
              {availableGroups.map((group) => (
                <label key={group.id} className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={selectedGroups.includes(group.id)}
                    onChange={() => toggleSelectedGroup(group.id)}
                  />
                  {group.name}
                </label>
              ))}
            </div>
            <button type="button" onClick={() => setIsGroupDialogOpen(false)}>
              Auswahl übernehmen
            </button>
          </div>
        </div>
      )}
      {uploadStatus && (
        <div className="auth-status" role="status">
          {uploadStatus}
        </div>
      )}
      {uploadError && (
        <div className="auth-error" role="alert">
          {uploadError}
        </div>
      )}
      {validationError && (
        <div className="auth-error" role="alert">
          {validationError}
        </div>
      )}
      <label>
        Name
        <input
          aria-label="Name"
          value={form.title}
          required
          maxLength={200}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
        />
      </label>
      <label>
        Kurzbeschreibung
        <textarea
          aria-label="Kurzbeschreibung"
          rows={3}
          value={form.description ?? ''}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
      </label>
      <label>
        Quelle
        <input
          aria-label="Quelle"
          placeholder="z. B. Kochbuchtitel oder URL"
          value={form.source ?? ''}
          maxLength={500}
          onChange={(e) => setForm({ ...form, source: e.target.value })}
        />
      </label>
      <div className="editor-block">
        <div className="section-heading compact">
          <h4>Rezeptbild</h4>
        </div>
        <input
          type="file"
          accept="image/*"
          onChange={handleRecipeImageUpload}
          disabled={busy || !recipe || !onUploadRecipeImage}
        />
        {form.recipe_image_key && <p className="muted">Key: {form.recipe_image_key}</p>}
        {recipeImageUrl && (
          <img className="instruction-preview" src={recipeImageUrl} alt="Rezeptbild" />
        )}
        {!recipe && (
          <p className="label-help">
            Für neue Rezepte zuerst einmal speichern, dann Bilder hochladen.
          </p>
        )}
      </div>
      <div className="form-grid three">
        <fieldset>
          <legend>Rezeptbücher</legend>
          {resolvedSingleGroupId &&
          availableGroups.find((group) => group.id === resolvedSingleGroupId) ? (
            <p className="muted">
              {availableGroups.find((group) => group.id === resolvedSingleGroupId)?.name}
            </p>
          ) : availableGroups.length === 0 ? (
            <p className="muted">Keine verfügbaren Rezeptbücher.</p>
          ) : (
            <div className="recipe-group-selector">
              <button
                type="button"
                className="button-secondary"
                onClick={() => setIsGroupDialogOpen(true)}
              >
                Rezeptbücher auswählen ({selectedGroups.length})
              </button>
              {selectedGroups.length === 0 ? (
                <p className="muted">Keine Rezeptbücher ausgewählt.</p>
              ) : (
                <div className="badge-row">
                  {availableGroups
                    .filter((group) => selectedGroups.includes(group.id))
                    .map((group) => (
                      <span key={group.id} className="badge">
                        {group.name}
                      </span>
                    ))}
                </div>
              )}
              <span className="label-help">
                Mehrfachauswahl über den Dialog. Mindestens ein Rezeptbuch ist erforderlich.
              </span>
            </div>
          )}
        </fieldset>
        <label>
          Schlagwörter <span className="label-help">mit Komma getrennt</span>
          <input value={tags} onChange={(e) => setTags(e.target.value)} />
        </label>
        <label>
          Portionen/Menge
          <input
            aria-label="Menge"
            type="number"
            min="0.01"
            step="0.01"
            value={form.yield.amount}
            onChange={(e) => setForm({ ...form, yield: { ...form.yield, amount: e.target.value } })}
          />
        </label>
      </div>
      <div className="form-grid four">
        <label>
          Einheit der Menge
          <input
            value={form.yield.unit}
            onChange={(e) => setForm({ ...form, yield: { ...form.yield, unit: e.target.value } })}
          />
        </label>
        {(['preparation_minutes', 'cooking_minutes', 'resting_minutes'] as const).map(
          (field, index) => (
            <label key={field}>
              {['Vorbereitung', 'Kochen', 'Ruhen'][index]} (Min.)
              <input
                type="number"
                min="0"
                value={form.time[field] ?? ''}
                onChange={(e) =>
                  setForm({
                    ...form,
                    time: {
                      ...form.time,
                      [field]: e.target.value === '' ? null : Number(e.target.value),
                    },
                  })
                }
              />
            </label>
          ),
        )}
      </div>

      <div className="editor-block">
        <div className="section-heading compact">
          <h4>Zutaten</h4>
          <button
            type="button"
            onClick={() =>
              setForm({ ...form, ingredient_sections: [...form.ingredient_sections, newSection()] })
            }
          >
            Abschnitt hinzufügen
          </button>
        </div>
        {form.ingredient_sections.map((section, sectionIndex) => (
          <div className="ingredient-section" key={section.id}>
            <div className="ingredient-section-header">
              <input
                aria-label={`Abschnitt ${sectionIndex + 1}`}
                placeholder="Abschnitt, z. B. Für den Teig"
                value={section.name ?? ''}
                onChange={(e) => updateSection(sectionIndex, { ...section, name: e.target.value })}
              />
              {form.ingredient_sections.length > 1 && (
                <button
                  type="button"
                  className="button-danger button-small"
                  onClick={() =>
                    setForm({
                      ...form,
                      ingredient_sections: form.ingredient_sections.filter(
                        (_, i) => i !== sectionIndex,
                      ),
                    })
                  }
                >
                  Abschnitt löschen
                </button>
              )}
            </div>
            {section.ingredients.map((ingredient, ingredientIndex) => (
              <div className="ingredient-row" key={`${section.id}-${ingredientIndex}`}>
                <input
                  aria-label="Menge der Zutat"
                  className="amount"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="Menge"
                  value={ingredient.amount ?? ''}
                  onChange={(e) =>
                    updateIngredient(sectionIndex, ingredientIndex, {
                      amount: e.target.value || null,
                    })
                  }
                />
                <select
                  aria-label="Einheit"
                  value={ingredient.unit}
                  onChange={(e) =>
                    updateIngredient(sectionIndex, ingredientIndex, {
                      unit: e.target.value as Unit,
                      custom_unit: e.target.value === 'custom' ? ingredient.custom_unit : null,
                    })
                  }
                >
                  {units.map((unit) => (
                    <option key={unit.value} value={unit.value}>
                      {unit.label}
                    </option>
                  ))}
                </select>
                {ingredient.unit === 'custom' && (
                  <input
                    aria-label="Eigene Einheit"
                    placeholder="Einheit"
                    value={ingredient.custom_unit ?? ''}
                    onChange={(e) =>
                      updateIngredient(sectionIndex, ingredientIndex, {
                        custom_unit: e.target.value,
                      })
                    }
                  />
                )}
                <input
                  aria-label="Zutat"
                  className="ingredient-name"
                  required={section.ingredients.length === 1}
                  placeholder="Zutat"
                  value={ingredient.name}
                  onChange={(e) =>
                    updateIngredient(sectionIndex, ingredientIndex, { name: e.target.value })
                  }
                />
                <input
                  aria-label="Vorbereitung"
                  placeholder="Vorbereitung"
                  value={ingredient.preparation ?? ''}
                  onChange={(e) =>
                    updateIngredient(sectionIndex, ingredientIndex, { preparation: e.target.value })
                  }
                />
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={ingredient.optional}
                    onChange={(e) =>
                      updateIngredient(sectionIndex, ingredientIndex, {
                        optional: e.target.checked,
                      })
                    }
                  />{' '}
                  optional
                </label>
                <button
                  type="button"
                  className="button-danger button-small"
                  aria-label="Zutat löschen"
                  onClick={() =>
                    updateSection(sectionIndex, {
                      ...section,
                      ingredients: section.ingredients.filter((_, i) => i !== ingredientIndex),
                    })
                  }
                >
                  ×
                </button>
              </div>
            ))}
            <button
              type="button"
              className="button-secondary"
              onClick={() =>
                updateSection(sectionIndex, {
                  ...section,
                  ingredients: [...section.ingredients, newIngredient()],
                })
              }
            >
              Zutat hinzufügen
            </button>
          </div>
        ))}
      </div>

      <div className="editor-block">
        <div className="section-heading compact">
          <h4>Zubereitung</h4>
          <button
            type="button"
            onClick={() =>
              setForm({
                ...form,
                instructions: [...form.instructions, { id: crypto.randomUUID(), text: '' }],
              })
            }
          >
            Schritt hinzufügen
          </button>
        </div>
        <ol className="instruction-editor">
          {form.instructions.map((step, index) => (
            <li key={step.id}>
              <div className="instruction-fields">
                <textarea
                  aria-label={`Zubereitungsschritt ${index + 1}`}
                  required={form.instructions.length === 1}
                  rows={2}
                  value={step.text}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      instructions: form.instructions.map((value, i) =>
                        i === index ? { ...value, text: e.target.value } : value,
                      ),
                    })
                  }
                />
                <input
                  type="file"
                  accept="image/*"
                  onChange={(event) => void handleInstructionImageUpload(step.id, event)}
                  disabled={busy || !recipe || !onUploadInstructionImage}
                />
                {step.image_key && <p className="muted">Key: {step.image_key}</p>}
                {stepImageUrls[step.id] && (
                  <img
                    className="instruction-preview"
                    src={stepImageUrls[step.id]}
                    alt={`Schrittbild ${index + 1}`}
                  />
                )}
              </div>
              <button
                type="button"
                className="button-danger button-small"
                aria-label="Schritt löschen"
                onClick={() =>
                  setForm({
                    ...form,
                    instructions: form.instructions.filter((_, i) => i !== index),
                  })
                }
              >
                ×
              </button>
            </li>
          ))}
        </ol>
      </div>
      <label>
        Bemerkungen
        <textarea
          aria-label="Bemerkungen"
          rows={3}
          value={form.remarks ?? ''}
          onChange={(e) => setForm({ ...form, remarks: e.target.value })}
        />
      </label>
    </form>
  );
}
