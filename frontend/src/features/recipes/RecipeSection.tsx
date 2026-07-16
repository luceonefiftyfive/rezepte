import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import type {
  ImageUploadResponse,
  Recipe,
  RecipePayload,
  SignedImageUrlResponse,
  Unit,
} from '../../types';
import { RecipeEditor } from './RecipeEditor';

const unitLabels: Record<Exclude<Unit, 'custom'>, string> = {
  g: 'g',
  kg: 'kg',
  ml: 'ml',
  l: 'l',
  tsp: 'TL',
  tbsp: 'EL',
  piece: 'Stück',
  pinch: 'Prise',
  bunch: 'Bund',
  clove: 'Zehe',
  slice: 'Scheibe',
  cup: 'Tasse',
  as_needed: 'nach Bedarf',
};

function getIngredientUnitLabel(unit: Unit, customUnit?: string | null): string {
  if (unit === 'custom') return customUnit?.trim() ?? '';
  return unitLabels[unit] ?? unit;
}

export function RecipeSection() {
  const { token } = useAuth();
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [editing, setEditing] = useState<Recipe | null>(null);
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState('');
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [recipePreviewImages, setRecipePreviewImages] = useState<
    Record<string, { key: string; url: string }>
  >({});
  const [recipeImageUrl, setRecipeImageUrl] = useState<string | null>(null);
  const [stepImageUrls, setStepImageUrls] = useState<Record<string, string>>({});

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

  async function uploadRecipeImage(recipeId: string, file: File): Promise<ImageUploadResponse> {
    const data = new FormData();
    data.append('file', file);
    return apiFetch<ImageUploadResponse>(
      `/recipes/${recipeId}/images/upload`,
      { method: 'POST', body: data },
      token,
    );
  }

  async function uploadInstructionImage(
    recipeId: string,
    stepId: string,
    file: File,
  ): Promise<ImageUploadResponse> {
    const data = new FormData();
    data.append('file', file);
    return apiFetch<ImageUploadResponse>(
      `/recipes/${recipeId}/instructions/${stepId}/image/upload`,
      { method: 'POST', body: data },
      token,
    );
  }

  async function refreshSelectedRecipeImageUrls(recipe: Recipe) {
    let nextRecipeImageUrl: string | null = null;
    const nextStepImageUrls: Record<string, string> = {};

    if (recipe.recipe_image_key) {
      const cached = recipePreviewImages[recipe.id];
      if (cached?.key === recipe.recipe_image_key) {
        nextRecipeImageUrl = cached.url;
      } else {
        try {
          const response = await apiFetch<SignedImageUrlResponse>(
            `/recipes/${recipe.id}/image-url`,
            {},
            token,
          );
          nextRecipeImageUrl = response.view_url;
          setRecipePreviewImages((current) => ({
            ...current,
            [recipe.id]: { key: recipe.recipe_image_key as string, url: response.view_url },
          }));
        } catch {
          nextRecipeImageUrl = null;
        }
      }
    }

    for (const step of recipe.instructions) {
      if (!step.image_key) continue;
      try {
        const response = await apiFetch<SignedImageUrlResponse>(
          `/recipes/${recipe.id}/instructions/${step.id}/image-url`,
          {},
          token,
        );
        nextStepImageUrls[step.id] = response.view_url;
      } catch {
        // Keep detail rendering resilient even with stale image keys.
      }
    }

    setRecipeImageUrl(nextRecipeImageUrl);
    setStepImageUrls(nextStepImageUrls);
  }

  useEffect(() => {
    void loadRecipes();
  }, [token]);

  useEffect(() => {
    let active = true;
    const recipesNeedingPreview = visibleRecipes.filter(
      (recipe) =>
        recipe.recipe_image_key && recipePreviewImages[recipe.id]?.key !== recipe.recipe_image_key,
    );

    if (recipesNeedingPreview.length === 0) {
      return () => {
        active = false;
      };
    }

    void Promise.all(
      recipesNeedingPreview.map(async (recipe) => {
        try {
          const response = await apiFetch<SignedImageUrlResponse>(
            `/recipes/${recipe.id}/image-url`,
            {},
            token,
          );
          return {
            id: recipe.id,
            key: recipe.recipe_image_key as string,
            url: response.view_url,
          };
        } catch {
          return null;
        }
      }),
    ).then((results) => {
      if (!active) return;
      const successful = results.filter((result) => result !== null);
      if (successful.length === 0) return;

      setRecipePreviewImages((current) => {
        const next = { ...current };
        for (const result of successful) {
          next[result.id] = { key: result.key, url: result.url };
        }
        return next;
      });
    });

    return () => {
      active = false;
    };
  }, [visibleRecipes, recipePreviewImages, token]);

  useEffect(() => {
    if (!selectedRecipe) {
      setRecipeImageUrl(null);
      setStepImageUrls({});
      return;
    }
    void refreshSelectedRecipeImageUrls(selectedRecipe);
  }, [recipePreviewImages, selectedRecipe, token]);

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
          <ul className="recipe-overview-grid">
            {visibleRecipes.map((recipe) => {
              const previewImageUrl =
                recipe.recipe_image_key &&
                recipePreviewImages[recipe.id]?.key === recipe.recipe_image_key
                  ? recipePreviewImages[recipe.id]?.url
                  : null;

              return (
                <li key={recipe.id}>
                  <button
                    type="button"
                    className={
                      selectedRecipe?.id === recipe.id ? 'recipe-overview-tile active' : 'recipe-overview-tile'
                    }
                    onClick={() => openRecipeDetail(recipe)}
                  >
                    {previewImageUrl && (
                      <img
                        className="recipe-overview-image"
                        src={previewImageUrl}
                        alt={`Vorschaubild ${recipe.title}`}
                        loading="lazy"
                      />
                    )}
                    {!previewImageUrl && (
                      <div className="recipe-overview-image recipe-overview-image--placeholder" aria-hidden="true" />
                    )}
                    <span className="recipe-overview-title">{recipe.title}</span>
                  </button>
                </li>
              );
            })}
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
            <div className="button-row">
              <button
                type="button"
                className="button-secondary"
                onClick={() => openRecipeEditor(selectedRecipe)}
              >
                Bearbeiten
              </button>
              <button
                className="button-danger"
                type="button"
                disabled={busy}
                onClick={() => void deleteRecipe(selectedRecipe)}
              >
                Löschen
              </button>
            </div>
          </div>
          {selectedRecipe.description && <p>{selectedRecipe.description}</p>}
          {recipeImageUrl && (
            <img
              className="recipe-detail-image"
              src={recipeImageUrl}
              alt={`Rezeptbild ${selectedRecipe.title}`}
            />
          )}
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
                    {ingredient.amount
                      ? `${ingredient.amount} ${getIngredientUnitLabel(ingredient.unit, ingredient.custom_unit)} `
                      : ''}
                    <strong>{ingredient.name}</strong>
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
                <li key={step.id}>
                  {step.text}
                  {stepImageUrls[step.id] && (
                    <img
                      className="recipe-step-image"
                      src={stepImageUrls[step.id]}
                      alt={`Schrittbild ${selectedRecipe.title}`}
                    />
                  )}
                </li>
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
        onUploadRecipeImage={uploadRecipeImage}
        onUploadInstructionImage={uploadInstructionImage}
      />
    </section>
  );
}
