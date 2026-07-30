import { useEffect, useMemo, useRef, useState } from 'react';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import { SectionUserInfo } from '../../components/SectionUserInfo';
import type {
  Group,
  ImageUploadResponse,
  RecipeListSort,
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

function TextWithLinks({ text }: { text?: string }) {
  if (!text) {
    return null;
  }

  const urlRegex = /(https?:\/\/[^\s<>"']+)/gi;

  return (
    <>
      {text.split(urlRegex).map((part, index) => {
        if (!/^https?:\/\//i.test(part)) {
          return <span key={index}>{part}</span>;
        }

        const match = part.match(/^(.*?)([.,;:!?)]*)$/);
        const url = match?.[1] ?? part;
        const trailingCharacters = match?.[2] ?? '';

        return (
          <span key={index}>
            <a href={url} target="_blank" rel="noopener noreferrer">
              {url}
            </a>
            {trailingCharacters}
          </span>
        );
      })}
    </>
  );
}

function formatIngredient(recipe: Recipe): string {
  return recipe.ingredient_sections
    .flatMap((section) => section.ingredients)
    .map((ingredient) => {
      const parts = [
        ingredient.amount ?? '',
        getIngredientUnitLabel(ingredient.unit, ingredient.custom_unit),
        ingredient.name,
        ingredient.preparation ?? '',
        ingredient.remarks ?? '',
      ];

      return parts
        .map((value) => value.trim())
        .filter(Boolean)
        .join(' ')
        .toLocaleLowerCase('de');
    })
    .join(' ');
}

interface RecipeSectionProps {
  searchQuery?: string;
  createRequestVersion?: number;
  overviewRequestVersion?: number;
}

export function RecipeSection({
  searchQuery = '',
  createRequestVersion = 0,
  overviewRequestVersion = 0,
}: RecipeSectionProps) {
  const { token, mayEditRecipes } = useAuth();
  const lastLoadedRecipeSelectionRef = useRef<string | null>(null);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [recipeSort, setRecipeSort] = useState<RecipeListSort>('created_desc');
  const [availableGroups, setAvailableGroups] = useState<Group[]>([]);
  const [manageableGroups, setManageableGroups] = useState<Group[]>([]);
  const [selectedViewGroupIds, setSelectedViewGroupIds] = useState<string[]>([]);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Recipe | null>(null);
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
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
  const editorGroups = useMemo(
    () => (manageableGroups.length > 0 ? manageableGroups : availableGroups),
    [manageableGroups, availableGroups],
  );

  const visibleRecipes = useMemo(() => {
    const needle = searchQuery.trim().toLocaleLowerCase('de');
    return recipes.filter((recipe) => {
      const matchesSearch =
        !needle ||
        [recipe.title, recipe.description ?? '', ...recipe.tags, formatIngredient(recipe)].some(
          (value) => value.toLocaleLowerCase('de').includes(needle),
        );
      const matchesTag = !selectedTag || recipe.tags.includes(selectedTag);
      return matchesSearch && matchesTag;
    });
  }, [recipes, searchQuery, selectedTag]);

  function getRecipeSelectionKey(
    groupIds: string[],
    groups: Group[],
    sort: RecipeListSort,
  ): string {
    const queryKey = groups.length > 1 ? groupIds.slice().sort().join(',') : '__all__';
    return `${token ?? 'anonymous'}:${queryKey}:${sort}`;
  }

  async function loadRecipes(
    groupIds = selectedViewGroupIds,
    groups = availableGroups,
    sort = recipeSort,
    options: { force?: boolean } = {},
  ) {
    setError('');

    if (!token) {
      lastLoadedRecipeSelectionRef.current = null;
      setRecipes([]);
      return;
    }

    if (groups.length > 0 && groupIds.length === 0) {
      lastLoadedRecipeSelectionRef.current = null;
      setRecipes([]);
      return;
    }

    const selectionKey = getRecipeSelectionKey(groupIds, groups, sort);
    if (!options.force && lastLoadedRecipeSelectionRef.current === selectionKey) {
      return;
    }

    try {
      const params = new URLSearchParams();
      params.set('sort', sort);
      if (groups.length > 1 && groupIds.length > 0) {
        params.set('group_ids', groupIds.join(','));
      }
      const query = params.size > 0 ? `?${params.toString()}` : '';
      setRecipes(await apiFetch<Recipe[]>(`/recipes${query}`, {}, token));
      lastLoadedRecipeSelectionRef.current = selectionKey;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    }
  }

  async function loadGroups() {
    setError('');
    try {
      const [viewGroups, editGroups] = await Promise.all([
        apiFetch<Group[]>('/groups', {}, token),
        mayEditRecipes
          ? apiFetch<Group[]>('/groups?manageable_only=true', {}, token)
          : Promise.resolve([]),
      ]);
      const nextSelectedViewGroupIds = (() => {
        const valid = selectedViewGroupIds.filter((id) =>
          viewGroups.some((group) => group.id === id),
        );
        if (valid.length > 0) return valid;
        return viewGroups.map((group) => group.id);
      })();

      setAvailableGroups(viewGroups);
      setManageableGroups(editGroups);
      setSelectedViewGroupIds(nextSelectedViewGroupIds);

      await loadRecipes(nextSelectedViewGroupIds, viewGroups, recipeSort);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    }
  }

  function toggleSelectedViewGroup(groupId: string) {
    setSelectedViewGroupIds((current) =>
      current.includes(groupId) ? current.filter((id) => id !== groupId) : [...current, groupId],
    );
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
      } else {
        await apiFetch<Recipe>(
          '/recipes',
          { method: 'POST', body: JSON.stringify(payload) },
          token,
        );
        setStatus('Rezept wurde gespeichert.');
      }
      setEditing(null);
      setIsEditorOpen(false);
      setSelectedRecipe(null);
      await loadRecipes(selectedViewGroupIds, availableGroups, recipeSort, { force: true });
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
      if (editing?.id === recipe.id) setIsEditorOpen(false);
      await loadRecipes(selectedViewGroupIds, availableGroups, recipeSort, { force: true });
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
    setIsEditorOpen(false);
  }

  function openRecipeEditor(recipe?: Recipe | null) {
    setSelectedRecipe(null);
    setEditing(recipe ?? null);
    setIsEditorOpen(true);
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
    lastLoadedRecipeSelectionRef.current = null;
    void loadGroups();
  }, [token, mayEditRecipes]);

  useEffect(() => {
    if (availableGroups.length === 0) return;
    void loadRecipes(selectedViewGroupIds, availableGroups, recipeSort);
  }, [token, availableGroups, selectedViewGroupIds, recipeSort]);

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

  useEffect(() => {
    if (createRequestVersion === 0) return;
    if (!mayEditRecipes) return;
    openRecipeEditor();
  }, [createRequestVersion, mayEditRecipes]);

  useEffect(() => {
    if (overviewRequestVersion === 0) return;
    setEditing(null);
    setIsEditorOpen(false);
    setSelectedRecipe(null);
  }, [overviewRequestVersion]);

  return (
    <section aria-labelledby="recipes-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Geschützter Bereich</p>
          <h2 id="recipes-heading">Rezepte</h2>
        </div>
        <div className="section-heading-actions">
          <SectionUserInfo />
          <button
            type="button"
            onClick={() =>
              void loadRecipes(selectedViewGroupIds, availableGroups, recipeSort, {
                force: true,
              })
            }
            disabled={busy}
          >
            Neu laden
          </button>
        </div>
      </div>
      {availableGroups.length > 1 && (
        <div className="card">
          <div className="section-heading compact">
            <h3>Rezeptbücher anzeigen</h3>
            <div className="button-row">
              <button
                type="button"
                className="button-secondary button-small"
                onClick={() => setSelectedViewGroupIds(availableGroups.map((group) => group.id))}
              >
                Alle
              </button>
            </div>
          </div>
          <div className="category-row">
            {availableGroups.map((group) => (
              <label key={group.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={selectedViewGroupIds.includes(group.id)}
                  onChange={() => toggleSelectedViewGroup(group.id)}
                />
                {group.name}
              </label>
            ))}
          </div>
        </div>
      )}
      {availableGroups.length === 1 && (
        <p className="muted">Aktives Rezeptbuch: {availableGroups[0].name}</p>
      )}
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
      {!isEditorOpen && (
        <div className="card">
          <div className="section-heading compact">
            <div>
              <h3>{selectedRecipe ? 'Rezept ansehen' : 'Gespeicherte Rezepte'}</h3>
              <p className="muted">
                {visibleRecipes.length} von {recipes.length}
              </p>
            </div>
            <div className="recipe-toolbar-actions">
              {!selectedRecipe && (
                <label>
                  <select
                    aria-label="Rezeptsortierung"
                    value={recipeSort}
                    onChange={(event) => setRecipeSort(event.target.value as RecipeListSort)}
                  >
                    <option value="created_desc">Nach Erstellung</option>
                    <option value="title_asc">Alphabetisch</option>
                  </select>
                </label>
              )}
              {selectedRecipe && (
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => setSelectedRecipe(null)}
                >
                  Zur Übersicht
                </button>
              )}
            </div>
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
          {!selectedRecipe &&
            (visibleRecipes.length === 0 ? (
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
                        aria-label={`Rezept anzeigen ${recipe.title}`}
                        className="recipe-overview-tile"
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
                          <div
                            className="recipe-overview-image recipe-overview-image--placeholder"
                            aria-hidden="true"
                          />
                        )}
                        <span className="recipe-overview-title">{recipe.title}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ))}

          {selectedRecipe && (
            <>
              <p className="muted">{selectedRecipe.title}</p>
              <div className="button-row">
                <button
                  type="button"
                  className="button-secondary"
                  disabled={!mayEditRecipes}
                  onClick={() => openRecipeEditor(selectedRecipe)}
                >
                  Bearbeiten
                </button>
                <button
                  className="button-danger"
                  type="button"
                  disabled={busy || !mayEditRecipes}
                  onClick={() => void deleteRecipe(selectedRecipe)}
                >
                  Löschen
                </button>
              </div>
              {selectedRecipe.description && <p>{selectedRecipe.description}</p>}
              {selectedRecipe.source && (
                <p>
                  <strong>Quelle:</strong> <TextWithLinks text={selectedRecipe.source} />
                </p>
              )}
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
                  <strong>Portionen:</strong> {selectedRecipe.yield.amount}{' '}
                  {selectedRecipe.yield.unit}
                </p>
                <p>
                  <strong>Vorbereitung:</strong> {selectedRecipe.time.preparation_minutes ?? '–'}{' '}
                  min · <strong>Kochen:</strong> {selectedRecipe.time.cooking_minutes ?? '–'} min ·{' '}
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
            </>
          )}
        </div>
      )}
      {isEditorOpen && (
        <RecipeEditor
          recipe={editing}
          availableGroups={editorGroups}
          forceSingleGroupId={editorGroups.length === 1 ? editorGroups[0].id : null}
          busy={busy}
          onSave={saveRecipe}
          onCancel={() => {
            setEditing(null);
            setIsEditorOpen(false);
          }}
          onUploadRecipeImage={uploadRecipeImage}
          onUploadInstructionImage={uploadInstructionImage}
        />
      )}
    </section>
  );
}
