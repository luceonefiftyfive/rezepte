import { ChangeEvent, FormEvent, useEffect, useState } from 'react';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import type { ImageUploadResponse, Recipe } from '../../types';

export function RecipeSection() {
  const { token } = useAuth();
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [title, setTitle] = useState('Apfelkuchen');
  const [description, setDescription] = useState('Ein Testrezept.');
  const [imageResult, setImageResult] = useState<ImageUploadResponse | null>(null);
  const [error, setError] = useState('');

  async function loadRecipes(): Promise<void> {
    setError('');
    try {
      setRecipes(await apiFetch<Recipe[]>('/recipes', {}, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }

  async function createRecipe(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError('');
    try {
      await apiFetch<Recipe>(
        '/recipes',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, description, tags: ['test', 'familienrezepte'] }),
        },
        token,
      );
      await loadRecipes();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }

  async function deleteRecipe(id: string): Promise<void> {
    setError('');
    try {
      await apiFetch<{ ok: boolean; deleted_id: string }>(
        `/recipes/${id}`,
        { method: 'DELETE' },
        token,
      );
      await loadRecipes();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }

  async function uploadImage(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    setError('');
    setImageResult(null);

    try {
      setImageResult(
        await apiFetch<ImageUploadResponse>(
          '/images/test-upload',
          { method: 'POST', body: formData },
          token,
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
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
          <p className="eyebrow">Protected area</p>
          <h2 id="recipes-heading">Recipe entry</h2>
        </div>
        <button type="button" onClick={() => void loadRecipes()}>Reload recipes</button>
      </div>

      {error && <div className="card error">{error}</div>}

      <div className="card">
        <h3>Create recipe</h3>
        <form onSubmit={createRecipe} className="form">
          <label>
            Title
            <input value={title} onChange={(event) => setTitle(event.target.value)} required />
          </label>
          <label>
            Description
            <input value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <button type="submit">Save recipe</button>
        </form>
      </div>

      <div className="card">
        <h3>Recipes</h3>
        {recipes.length === 0 ? (
          <p>No recipes yet.</p>
        ) : (
          <ul className="recipe-list">
            {recipes.map((recipe) => (
              <li key={recipe.id}>
                <div>
                  <strong>{recipe.title}</strong>
                  <p>{recipe.description}</p>
                  <small>{recipe.created_at}</small>
                </div>
                <button type="button" onClick={() => void deleteRecipe(recipe.id)}>Delete</button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="card">
        <h3>Upload image</h3>
        <input type="file" accept="image/*" onChange={uploadImage} />
        {imageResult && <pre>{JSON.stringify(imageResult, null, 2)}</pre>}
      </div>
    </section>
  );
}
