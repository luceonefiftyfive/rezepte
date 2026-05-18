import { ChangeEvent, FormEvent, useEffect, useState } from "react";

const API_BASE = "/api";

type HealthResponse = {
  status: string;
  service: string;
  time: string;
};

type SystemCheckItem = {
  ok: boolean;
  endpoint?: string;
  bucket?: string;
  error?: string;
};

type SystemChecksResponse = {
  api: SystemCheckItem;
  mongodb: SystemCheckItem;
  s3: SystemCheckItem;
  ok: boolean;
};

type Recipe = {
  id: string;
  title: string;
  description: string | null;
  tags: string[];
  created_at: string;
};

type ImageUploadResponse = {
  ok: boolean;
  bucket: string;
  key: string;
  size: number;
  content_type: string;
};

async function fetchJson<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, options);

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }

  return response.json() as Promise<T>;
}

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [checks, setChecks] = useState<SystemChecksResponse | null>(null);
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [title, setTitle] = useState<string>("Apfelkuchen");
  const [description, setDescription] = useState<string>("Ein Testrezept.");
  const [imageResult, setImageResult] = useState<ImageUploadResponse | null>(
    null
  );
  const [error, setError] = useState<string>("");

  async function loadHealth(): Promise<void> {
    setError("");

    try {
      const data = await fetchJson<HealthResponse>("/health");
      setHealth(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  async function loadChecks(): Promise<void> {
    setError("");

    try {
      const data = await fetchJson<SystemChecksResponse>("/system/checks");
      setChecks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  async function loadRecipes(): Promise<void> {
    setError("");

    try {
      const data = await fetchJson<Recipe[]>("/recipes");
      setRecipes(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  async function createRecipe(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setError("");

    try {
      await fetchJson<Recipe>("/recipes", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          title,
          description,
          tags: ["test", "familienrezepte"]
        })
      });

      await loadRecipes();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  async function deleteRecipe(id: string): Promise<void> {
    setError("");

    try {
      await fetchJson<{ ok: boolean; deleted_id: string }>(`/recipes/${id}`, {
        method: "DELETE"
      });

      await loadRecipes();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    }
  }

  async function uploadImage(
    event: ChangeEvent<HTMLInputElement>
  ): Promise<void> {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    setError("");
    setImageResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const data = await fetchJson<ImageUploadResponse>("/images/test-upload", {
        method: "POST",
        body: formData
      });

      setImageResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      event.target.value = "";
    }
  }

  useEffect(() => {
    void loadHealth();
    void loadChecks();
    void loadRecipes();
  }, []);

  return (
    <main className="page">
      <section className="hero">
        <div>
          <p className="eyebrow">Server installation test</p>
          <h1>Familienrezepte</h1>
          <p>
            This test frontend verifies nginx, FastAPI, MongoDB and
            S3-compatible storage.
          </p>
        </div>

        <div className="button-row">
          <button type="button" onClick={() => void loadHealth()}>
            Check API
          </button>
          <button type="button" onClick={() => void loadChecks()}>
            Check services
          </button>
          <button type="button" onClick={() => void loadRecipes()}>
            Reload recipes
          </button>
        </div>
      </section>

      {error && (
        <section className="card error">
          <strong>Error</strong>
          <pre>{error}</pre>
        </section>
      )}

      <section className="grid">
        <div className="card">
          <h2>API health</h2>
          <pre>{JSON.stringify(health, null, 2)}</pre>
        </div>

        <div className="card">
          <h2>System checks</h2>
          <pre>{JSON.stringify(checks, null, 2)}</pre>
        </div>
      </section>

      <section className="card">
        <h2>Create test recipe</h2>

        <form onSubmit={createRecipe} className="form">
          <label>
            Title
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
          </label>

          <label>
            Description
            <input
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </label>

          <button type="submit">Save recipe to MongoDB</button>
        </form>
      </section>

      <section className="card">
        <h2>Recipes from MongoDB</h2>

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

                <button
                  type="button"
                  onClick={() => void deleteRecipe(recipe.id)}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2>S3 test upload</h2>

        <p>Upload an image. The backend stores it in MinIO/S3.</p>

        <input type="file" accept="image/*" onChange={uploadImage} />

        {imageResult && <pre>{JSON.stringify(imageResult, null, 2)}</pre>}
      </section>

      <section className="card">
        <h2>Useful test URLs</h2>
        <ul>
          <li>
            <a href="/api/health" target="_blank" rel="noreferrer">
              /api/health
            </a>
          </li>
          <li>
            <a href="/api/system/checks" target="_blank" rel="noreferrer">
              /api/system/checks
            </a>
          </li>
          <li>
            <a href="/auth/" target="_blank" rel="noreferrer">
              /auth/
            </a>
          </li>
        </ul>
      </section>
    </main>
  );
}