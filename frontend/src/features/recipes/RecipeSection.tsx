import { ChangeEvent, useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import type { ImageUploadResponse, Recipe, RecipePayload } from '../../types';
import { RecipeEditor } from './RecipeEditor';

function formatDate(value: string): string { const date = new Date(value); return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('de-DE', { dateStyle: 'medium', timeStyle: 'short' }).format(date); }
function formatIngredient(recipe: Recipe): string { return recipe.ingredient_sections.flatMap((section) => section.ingredients.map((item) => item.name)).join(', '); }

export function RecipeSection() {
  const { token } = useAuth();
  const [recipes, setRecipes] = useState<Recipe[]>([]); const [editing, setEditing] = useState<Recipe | null>(null); const [search, setSearch] = useState('');
  const [imageResult, setImageResult] = useState<ImageUploadResponse | null>(null); const [error, setError] = useState(''); const [status, setStatus] = useState(''); const [busy, setBusy] = useState(false);
  const visibleRecipes = useMemo(() => { const needle = search.trim().toLocaleLowerCase('de'); if (!needle) return recipes; return recipes.filter((recipe) => [recipe.title, recipe.description ?? '', ...recipe.tags, formatIngredient(recipe)].some((value) => value.toLocaleLowerCase('de').includes(needle))); }, [recipes, search]);
  async function loadRecipes() { setError(''); try { setRecipes(await apiFetch<Recipe[]>('/recipes', {}, token)); } catch (err) { setError(err instanceof Error ? err.message : 'Unbekannter Fehler'); } }
  async function saveRecipe(payload: RecipePayload, version?: number) { setBusy(true); setError(''); setStatus(''); try { if (editing && version) { await apiFetch<Recipe>(`/recipes/${editing.id}`, { method: 'PUT', body: JSON.stringify({ ...payload, version }) }, token); setStatus('Rezept wurde aktualisiert.'); setEditing(null); } else { await apiFetch<Recipe>('/recipes', { method: 'POST', body: JSON.stringify(payload) }, token); setStatus('Rezept wurde gespeichert.'); } await loadRecipes(); } catch (err) { setError(err instanceof Error ? err.message : 'Unbekannter Fehler'); } finally { setBusy(false); } }
  async function deleteRecipe(recipe: Recipe) { if (!window.confirm(`Rezept „${recipe.title}“ wirklich löschen?`)) return; setBusy(true); try { await apiFetch(`/recipes/${recipe.id}`, { method: 'DELETE' }, token); if (editing?.id === recipe.id) setEditing(null); await loadRecipes(); setStatus('Rezept wurde gelöscht.'); } catch (err) { setError(err instanceof Error ? err.message : 'Unbekannter Fehler'); } finally { setBusy(false); } }
  async function uploadImage(event: ChangeEvent<HTMLInputElement>) { const file = event.target.files?.[0]; if (!file) return; const data = new FormData(); data.append('file', file); setBusy(true); try { setImageResult(await apiFetch('/images/test-upload', { method: 'POST', body: data }, token)); setStatus('Bild wurde hochgeladen.'); } catch (err) { setError(err instanceof Error ? err.message : 'Unbekannter Fehler'); } finally { setBusy(false); event.target.value = ''; } }
  useEffect(() => { void loadRecipes(); }, [token]);

  return <section aria-labelledby="recipes-heading"><div className="section-heading"><div><p className="eyebrow">Geschützter Bereich</p><h2 id="recipes-heading">Rezepte</h2></div><button type="button" onClick={() => void loadRecipes()} disabled={busy}>Neu laden</button></div>
    {status && <div className="auth-status" role="status">{status}</div>}{error && <div className="auth-error" role="alert">{error}</div>}
    <RecipeEditor recipe={editing} busy={busy} onSave={saveRecipe} onCancel={() => setEditing(null)} />
    <div className="card image-upload-card"><h3>Bild-Upload testen</h3><input type="file" accept="image/*" onChange={uploadImage} disabled={busy} />{imageResult && <p className="muted">Gespeichert als: {imageResult.key}</p>}</div>
    <div className="card"><div className="section-heading compact"><div><h3>Gespeicherte Rezepte</h3><p className="muted">{visibleRecipes.length} von {recipes.length}</p></div><label className="search-field">Suchen<input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Name, Zutat oder Schlagwort" /></label></div>
      {visibleRecipes.length === 0 ? <p>Keine passenden Rezepte vorhanden.</p> : <ul className="recipe-list">{visibleRecipes.map((recipe) => <li key={recipe.id}><div className="recipe-content"><strong>{recipe.title}</strong>{recipe.description && <p>{recipe.description}</p>}<p className="muted"><b>Zutaten:</b> {formatIngredient(recipe) || 'keine'}</p><p className="muted"><b>Zubereitung:</b> {recipe.instructions.length} Schritte</p><div className="badge-row">{recipe.tags.map((tag) => <span className="badge" key={tag}>{tag}</span>)}</div><small className="muted">Aktualisiert: {formatDate(recipe.updated_at)} · Version {recipe.version}</small></div><div className="user-card__actions"><button type="button" className="button-secondary" onClick={() => { setEditing(recipe); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>Bearbeiten</button><button className="button-danger" type="button" disabled={busy} onClick={() => void deleteRecipe(recipe)}>Löschen</button></div></li>)}</ul>}
    </div>
  </section>;
}
