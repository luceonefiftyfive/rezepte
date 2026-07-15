import { ChangeEvent, useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import type { ImageUploadResponse, Recipe, RecipePayload } from '../../types';
import { RecipeEditor } from './RecipeEditor';

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}
function formatIngredient(recipe: Recipe): string {
  return recipe.ingredient_sections
    .flatMap((section) => section.ingredients.map((item) => item.name))
    .join(', ');
}

export function RecipeSection() {
  const { token } = useAuth();
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [editing, setEditing] = useState<Recipe | null>(null);
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState('');
  const [imageResult, setImageResult] = useState<ImageUploadResponse | null>(null);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);

  const availableTags = useMemo(
    () => Array.from(new Set(recipes.flatMap((recipe) => recipe.tags))).sort(),
    [recipes],
  );

  const visibleRecipes = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase('de');
    return recipes.filter((recipe) => {
      const matchesSearch =
        !needle ||
        [recipe.title, recipe.description ?? '', ...recipe.tags, formatIngredient(recipe)].some(
          (value) => value.toLocaleLowerCase('de').includes(needle),
        );
      const matchesTag = !selectedTag || recipe.tags.includes(selectedTag);
      return matchesSearch && matchesTag;
    });
  }, [recipes, search, selectedTag]);

  async function loadRecipes() {
    setError('');
    try {
      setRecipes(await apiFetch<Recipe[]>('/recipes', {}, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    }
  }

  async function saveRecipe(payload: RecipePayload, version?: number) {
    setBusy(true);
    setError('');
    setStatus('');
    try {
      if (editing && version) {
        await apiFetch<Recipe>(
          `/recipes/${editing.id}`,
          { method: 'PUT', body: JSON.stringify({ ...payload, version }) },
          token,
        );
        setStatus('Rezept wurde aktualisiert.');
        setEditing(null);
      } else {
        await apiFetch<Recipe>(
          '/recipes',
          { method: 'POST', body: JSON.stringify(payload) },
          token,
        );
        setStatus('Rezept wurde gespeichert.');
      }
      setSelectedRecipe(null);
      await loadRecipes();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  async function deleteRecipe(recipe: Recipe) {
    if (!window.confirm(`Rezept „${recipe.title}“ wirklich löschen?`)) return;
    setBusy(true);
    try {
      await apiFetch(`/recipes/${recipe.id}`, { method: 'DELETE' }, token);
      if (editing?.id === recipe.id) setEditing(null);
      if (selectedRecipe?.id === recipe.id) setSelectedRecipe(null);
      await loadRecipes();
      setStatus('Rezept wurde gelöscht.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  function openRecipeDetail(recipe: Recipe) {
    setSelectedRecipe(recipe);
    setEditing(null);
  }

  function openRecipeEditor(recipe?: Recipe | null) {
    setSelectedRecipe(null);
    setEditing(recipe ?? null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function uploadImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const data = new FormData();
    data.append('file', file);

    setBusy(true);
    try {
      setImageResult(await apiFetch('/images/test-upload', { method: 'POST', body: data }, token));
      setStatus('Bild wurde hochgeladen.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
      event.target.value = '';
    }
  }

  useEffect(() => {
    void loadRecipes();
  }, [token]);

  return (
    <section aria-labelledby="recipes-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Geschützter Bereich</p>
          <h2 id="recipes-heading">Rezepte</h2>
        </div>
        <div>
          <button type="button" onClick={() => void loadRecipes()} disabled={busy}>
            Neu laden
          </button>
          <button
            type="button"
            className="button-secondary"
            onClick={() => openRecipeEditor()}
            disabled={busy}
          >
            Neues Rezept
          </button>
        </div>
      </div>
      {status && (
        <div className="auth-status" role="status">
          {status}
        </div>
      )}
      {error && (
        <div className="auth-error" role="alert">
          {error}
        </div>
      )}
      <div className="card">
        <div className="section-heading compact">
          <div>
            <h3>Gespeicherte Rezepte</h3>
            <p className="muted">
              {visibleRecipes.length} von {recipes.length}
            </p>
          </div>
          <label className="search-field">
            Suchen
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Name, Zutat oder Schlagwort"
            />
          </label>
        </div>
        {availableTags.length > 0 && (
          <div className="category-row">
            <button
              type="button"
              className={selectedTag === '' ? 'badge badge--active' : 'badge badge--ghost'}
              onClick={() => setSelectedTag('')}
            >
              Alle
            </button>
            {availableTags.map((tag) => (
              <button
                key={tag}
                type="button"
                className={selectedTag === tag ? 'badge badge--active' : 'badge badge--ghost'}
                onClick={() => setSelectedTag(tag)}
              >
                {tag}
              </button>
            ))}
          </div>
        )}
        {visibleRecipes.length === 0 ? (
          <p>Keine passenden Rezepte vorhanden.</p>
        ) : (
          <ul className="recipe-list">
            {visibleRecipes.map((recipe) => (
              <li key={recipe.id} className="recipe-card">
                <article>
                  <header className="recipe-card-header">
                    <h3>{recipe.title}</h3>
                    <small className="muted">
                      Aktualisiert: {formatDate(recipe.updated_at)} · Version {recipe.version}
                    </small>
                  </header>
                  {recipe.description && <p>{recipe.description}</p>}
                  <div className="badge-row">
                    {recipe.tags.map((tag) => (
                      <span className="badge" key={tag}>
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="recipe-card-meta">
                    <span>{formatIngredient(recipe) || 'keine Zutaten'}</span>
                    <span>{recipe.instructions.length} Schritte</span>
                  </div>
                </article>
                <div className="recipe-card-actions">
                  <button type="button" onClick={() => openRecipeDetail(recipe)}>
                    Anzeigen
                  </button>
                  <button
                    type="button"
                    className="button-secondary"
                    onClick={() => openRecipeEditor(recipe)}
                  >
                    Bearbeiten
                  </button>
                  <button
                    className="button-danger"
                    type="button"
                    disabled={busy}
                    onClick={() => void deleteRecipe(recipe)}
                  >
                    Löschen
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
      {selectedRecipe && (
        <div className="card">
          <div className="section-heading compact">
            <div>
              <h3>Rezept ansehen</h3>
              <p className="muted">{selectedRecipe.title}</p>
            </div>
            <button
              type="button"
              className="button-secondary"
              onClick={() => openRecipeEditor(selectedRecipe)}
            >
              Bearbeiten
            </button>
          </div>
          {selectedRecipe.description && <p>{selectedRecipe.description}</p>}
          <div className="recipe-detail-meta">
            <p>
              <strong>Rezeptbücher:</strong> {selectedRecipe.group_ids.join(', ') || 'keine'}
            </p>
            <p>
              <strong>Schlagwörter:</strong> {selectedRecipe.tags.join(', ') || 'keine'}
            </p>
            <p>
              <strong>Portionen:</strong> {selectedRecipe.yield.amount} {selectedRecipe.yield.unit}
            </p>
            <p>
              <strong>Vorbereitung:</strong> {selectedRecipe.time.preparation_minutes ?? '–'} min ·{' '}
              <strong>Kochen:</strong> {selectedRecipe.time.cooking_minutes ?? '–'} min ·{' '}
              <strong>Ruhen:</strong> {selectedRecipe.time.resting_minutes ?? '–'} min
            </p>
          </div>
          {selectedRecipe.ingredient_sections.map((section) => (
            <div key={section.id}>
              <h4>{section.name ?? 'Zutaten'}</h4>
              <ul>
                {section.ingredients.map((ingredient, index) => (
                  <li key={`${section.id}-${index}`}>
                    <strong>{ingredient.name}</strong>
                    {ingredient.amount
                      ? ` — ${ingredient.amount} ${ingredient.unit === 'custom' ? (ingredient.custom_unit ?? '') : ingredient.unit}`
                      : ''}
                    {ingredient.preparation ? `, ${ingredient.preparation}` : ''}
                    {ingredient.optional ? ' (optional)' : ''}
                    {ingredient.remarks ? ` — ${ingredient.remarks}` : ''}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <div>
            <h4>Zubereitung</h4>
            <ol>
              {selectedRecipe.instructions.map((step) => (
                <li key={step.id}>{step.text}</li>
              ))}
            </ol>
          </div>
          {selectedRecipe.remarks && (
            <div>
              <h4>Bemerkungen</h4>
              <p>{selectedRecipe.remarks}</p>
            </div>
          )}
        </div>
      )}
      <RecipeEditor
        recipe={editing}
        busy={busy}
        onSave={saveRecipe}
        onCancel={() => setEditing(null)}
      />
      <div className="card image-upload-card">
        <h3>Bild-Upload testen</h3>
        <input type="file" accept="image/*" onChange={uploadImage} disabled={busy} />
        {imageResult && <p className="muted">Gespeichert als: {imageResult.key}</p>}
      </div>
    </section>
  );
}
