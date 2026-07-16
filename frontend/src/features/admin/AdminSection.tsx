import { FormEvent, useEffect, useState } from 'react';
import { apiFetch, apiFetchText } from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import type {
  GroupRole,
  RecipeExportFormat,
  RecipeImportPreviewResponse,
  RecipeImportResponse,
  RecipePurgeResponse,
  Role,
  UserPublic,
} from '../../types';

type NewUserForm = {
  username: string;
  password: string;
  first_name: string;
  last_name: string;
  email: string;
  group_id: string;
  role: Role;
  is_super_admin: boolean;
};

const EMPTY_NEW_USER: NewUserForm = {
  username: '',
  password: '',
  first_name: '',
  last_name: '',
  email: '',
  group_id: 'recipes',
  role: 'reader',
  is_super_admin: false,
};

export function AdminSection() {
  const { token, user: currentUser, refreshUser } = useAuth();
  const [users, setUsers] = useState<UserPublic[]>([]);
  const [newUser, setNewUser] = useState<NewUserForm>(EMPTY_NEW_USER);
  const [groupDrafts, setGroupDrafts] = useState<Record<string, GroupRole[]>>({});
  const [recipeGroupFilter, setRecipeGroupFilter] = useState('');
  const [recipeImportFormat, setRecipeImportFormat] = useState<RecipeExportFormat>('yaml');
  const [recipeImportContent, setRecipeImportContent] = useState('');
  const [recipeImportPreview, setRecipeImportPreview] =
    useState<RecipeImportPreviewResponse | null>(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function loadUsers(): Promise<void> {
    setError('');
    try {
      const data = await apiFetch<UserPublic[]>('/users', {}, token);
      setUsers(data);
      setGroupDrafts(Object.fromEntries(data.map((user) => [user.id, user.groups])));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    }
  }

  useEffect(() => {
    void loadUsers();
  }, [token]);

  async function createUser(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setError('');
    setStatus('');
    try {
      const groups = newUser.group_id.trim()
        ? [{ group_id: newUser.group_id.trim(), role: newUser.role }]
        : [];
      await apiFetch<UserPublic>(
        '/users',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: newUser.username.trim(),
            password: newUser.password,
            first_name: newUser.first_name.trim(),
            last_name: newUser.last_name.trim(),
            email: newUser.email.trim(),
            groups,
            is_super_admin: currentUser?.is_super_admin ? newUser.is_super_admin : false,
          }),
        },
        token,
      );
      setStatus(`Benutzer ${newUser.username} wurde angelegt`);
      setNewUser(EMPTY_NEW_USER);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  function updateGroup(userId: string, index: number, patch: Partial<GroupRole>): void {
    setGroupDrafts((current) => ({
      ...current,
      [userId]: (current[userId] ?? []).map((group, i) =>
        i === index ? { ...group, ...patch } : group,
      ),
    }));
  }

  function addGroup(userId: string): void {
    setGroupDrafts((current) => ({
      ...current,
      [userId]: [...(current[userId] ?? []), { group_id: '', role: 'reader' }],
    }));
  }

  function removeGroup(userId: string, index: number): void {
    setGroupDrafts((current) => ({
      ...current,
      [userId]: (current[userId] ?? []).filter((_, i) => i !== index),
    }));
  }

  async function saveGroups(user: UserPublic): Promise<void> {
    const groups = (groupDrafts[user.id] ?? []).map((group) => ({
      ...group,
      group_id: group.group_id.trim(),
    }));
    if (groups.some((group) => !group.group_id)) {
      setError('Für jede Gruppe muss eine Gruppen-ID angegeben werden.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await apiFetch<UserPublic>(
        `/users/${user.id}/groups`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ groups }),
        },
        token,
      );
      setStatus(`Gruppenzuordnungen für ${user.username} wurden aktualisiert`);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  async function setSuperAdministrator(
    user: UserPublic,
    isSuperAdministrator: boolean,
  ): Promise<void> {
    setBusy(true);
    setError('');
    try {
      await apiFetch<UserPublic>(
        `/users/${user.id}/super-admin`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ is_super_admin: isSuperAdministrator }),
        },
        token,
      );
      await loadUsers();
      if (user.id === currentUser?.id) await refreshUser();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  async function deactivateUser(user: UserPublic): Promise<void> {
    if (!window.confirm(`Benutzer „${user.username}“ deaktivieren?`)) return;
    setBusy(true);
    setError('');
    try {
      await apiFetch<{ deleted: boolean }>(`/users/${user.id}`, { method: 'DELETE' }, token);
      setStatus(`${user.username} wurde deaktiviert`);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  function buildRecipeAdminQuery(): string {
    const groupId = recipeGroupFilter.trim();
    if (!groupId) return '';
    return `?group_id=${encodeURIComponent(groupId)}`;
  }

  async function exportRecipes(exportFormat: RecipeExportFormat): Promise<void> {
    setBusy(true);
    setError('');
    setStatus('');
    try {
      const query = buildRecipeAdminQuery();
      const content = await apiFetchText(
        `/recipes/admin/export?format=${exportFormat}${query ? `&${query.slice(1)}` : ''}`,
        {},
        token,
      );
      const now = new Date();
      const datePart = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
      const extension = exportFormat === 'yaml' ? 'yaml' : 'md';
      const fileName = `rezepte-export-${datePart}.${extension}`;
      const blob = new Blob([content], {
        type: exportFormat === 'yaml' ? 'application/x-yaml' : 'text/markdown',
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = fileName;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setStatus(`Export (${exportFormat.toUpperCase()}) wurde heruntergeladen.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  async function purgeRecipes(): Promise<void> {
    const groupId = recipeGroupFilter.trim();
    const message = groupId
      ? `Alle Rezepte der Gruppe „${groupId}“ löschen?`
      : 'Wirklich alle Rezepte löschen?';
    if (!window.confirm(message)) return;

    setBusy(true);
    setError('');
    setStatus('');
    try {
      const query = buildRecipeAdminQuery();
      const response = await apiFetch<RecipePurgeResponse>(
        `/recipes/admin/purge${query}`,
        { method: 'DELETE' },
        token,
      );
      setStatus(`${response.deleted_count} Rezepte wurden gelöscht.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  async function importRecipes(): Promise<void> {
    const content = recipeImportContent.trim();
    if (!content) {
      setError('Bitte Import-Inhalt einfügen.');
      return;
    }

    setBusy(true);
    setError('');
    setStatus('');
    try {
      const response = await apiFetch<RecipeImportResponse>(
        '/recipes/admin/import',
        {
          method: 'POST',
          body: JSON.stringify({ format: recipeImportFormat, content }),
        },
        token,
      );
      setRecipeImportPreview(null);
      setStatus(
        `Import abgeschlossen: ${response.imported} verarbeitet (${response.created} neu, ${response.updated} aktualisiert).`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  async function previewImportRecipes(): Promise<void> {
    const content = recipeImportContent.trim();
    if (!content) {
      setError('Bitte Import-Inhalt einfügen.');
      return;
    }

    setBusy(true);
    setError('');
    setStatus('');
    try {
      const response = await apiFetch<RecipeImportPreviewResponse>(
        '/recipes/admin/import/preview',
        {
          method: 'POST',
          body: JSON.stringify({ format: recipeImportFormat, content }),
        },
        token,
      );
      setRecipeImportPreview(response);
      setStatus(
        `Vorschau: ${response.imported} Rezepte geprüft (${response.would_create} neu, ${response.would_update} Update).`,
      );
    } catch (err) {
      setRecipeImportPreview(null);
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="admin-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Geschützter Bereich</p>
          <h2 id="admin-heading">Benutzerverwaltung</h2>
        </div>
        <button type="button" onClick={() => void loadUsers()} disabled={busy}>
          Benutzer neu laden
        </button>
      </div>
      {status && <div className="auth-status">{status}</div>}
      {error && <div className="auth-error">{error}</div>}

      <section className="card" aria-labelledby="recipe-admin-tools-heading">
        <h3 id="recipe-admin-tools-heading">Rezepte: Export, Import und Bereinigung</h3>
        <div className="form-grid">
          <label>
            Gruppen-ID (optional)
            <input
              value={recipeGroupFilter}
              onChange={(event) => setRecipeGroupFilter(event.target.value)}
              placeholder="z.B. family"
            />
          </label>
          <label>
            Import-Format
            <select
              value={recipeImportFormat}
              onChange={(event) => setRecipeImportFormat(event.target.value as RecipeExportFormat)}
            >
              <option value="yaml">YAML</option>
              <option value="markdown">Markdown</option>
            </select>
          </label>
        </div>
        <div className="button-row">
          <button type="button" disabled={busy} onClick={() => void exportRecipes('yaml')}>
            Export YAML
          </button>
          <button
            type="button"
            className="button-secondary"
            disabled={busy}
            onClick={() => void exportRecipes('markdown')}
          >
            Export Markdown
          </button>
          <button
            type="button"
            className="button-danger"
            disabled={busy}
            onClick={() => void purgeRecipes()}
          >
            Löschen (alle/Gruppe)
          </button>
        </div>
        <label>
          Import-Inhalt
          <textarea
            rows={10}
            value={recipeImportContent}
            onChange={(event) => setRecipeImportContent(event.target.value)}
            placeholder="Exportierten YAML- oder Markdown-Inhalt hier einfügen"
          />
        </label>
        <div className="button-row">
          <button
            type="button"
            className="button-secondary"
            disabled={busy}
            onClick={() => void previewImportRecipes()}
          >
            Import prüfen
          </button>
          <button type="button" disabled={busy} onClick={() => void importRecipes()}>
            Import starten
          </button>
        </div>
        {recipeImportPreview && (
          <p className="muted">
            Vorschau-Ergebnis: {recipeImportPreview.imported} geprüft,{' '}
            {recipeImportPreview.would_create} neu, {recipeImportPreview.would_update} würden
            aktualisiert.
          </p>
        )}
      </section>

      <form onSubmit={createUser} className="card user-create-form">
        <h3>Benutzer anlegen</h3>
        <div className="form-grid">
          <label>
            Benutzername
            <input
              value={newUser.username}
              onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
              required
            />
          </label>
          <label>
            Passwort
            <input
              type="password"
              minLength={8}
              value={newUser.password}
              onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
              required
            />
          </label>
          <label>
            Vorname
            <input
              value={newUser.first_name}
              onChange={(e) => setNewUser({ ...newUser, first_name: e.target.value })}
              required
            />
          </label>
          <label>
            Nachname
            <input
              value={newUser.last_name}
              onChange={(e) => setNewUser({ ...newUser, last_name: e.target.value })}
              required
            />
          </label>
          <label>
            Email
            <input
              type="email"
              value={newUser.email}
              onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
              required
            />
          </label>
          <label>
            Gruppen-ID
            <input
              value={newUser.group_id}
              onChange={(e) => setNewUser({ ...newUser, group_id: e.target.value })}
            />
          </label>
          <label>
            Role
            <select
              value={newUser.role}
              onChange={(e) => setNewUser({ ...newUser, role: e.target.value as Role })}
            >
              <option value="reader">Leser</option>
              <option value="author">Autor</option>
              <option value="admin">Administrator</option>
            </select>
          </label>
          {currentUser?.is_super_admin && (
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={newUser.is_super_admin}
                onChange={(e) => setNewUser({ ...newUser, is_super_admin: e.target.checked })}
              />
              Super-Admin
            </label>
          )}
        </div>
        <button type="submit" disabled={busy}>
          Benutzer anlegen
        </button>
      </form>

      <div className="user-list">
        {users.map((user) => (
          <article
            className={`card user-card ${!user.is_active ? 'user-card--inactive' : ''}`}
            key={user.id}
          >
            <div className="user-card__header">
              <div>
                <h3>
                  {user.first_name} {user.last_name}
                </h3>
                <p className="muted">
                  @{user.username} · {user.email}
                </p>
              </div>
              <div className="badge-row">
                {user.is_super_admin && <span className="badge">Super-Admin</span>}
                {!user.is_active && <span className="badge badge--danger">Inaktiv</span>}
              </div>
            </div>
            <div className="group-editor">
              <strong>Gruppenrollen</strong>
              {(groupDrafts[user.id] ?? []).map((group, index) => (
                <div className="group-row" key={`${user.id}-${index}`}>
                  <input
                    value={group.group_id}
                    onChange={(e) => updateGroup(user.id, index, { group_id: e.target.value })}
                  />
                  <select
                    value={group.role}
                    onChange={(e) => updateGroup(user.id, index, { role: e.target.value as Role })}
                  >
                    <option value="reader">Leser</option>
                    <option value="author">Autor</option>
                    <option value="admin">Administrator</option>
                  </select>
                  <button
                    type="button"
                    className="button-danger button-small"
                    onClick={() => removeGroup(user.id, index)}
                  >
                    Entfernen
                  </button>
                </div>
              ))}
              <div className="button-row">
                <button
                  type="button"
                  className="button-secondary button-small"
                  onClick={() => addGroup(user.id)}
                >
                  Gruppe hinzufügen
                </button>
                <button
                  type="button"
                  className="button-small"
                  disabled={busy || !user.is_active}
                  onClick={() => void saveGroups(user)}
                >
                  Gruppen speichern
                </button>
              </div>
            </div>
            {currentUser?.is_super_admin && (
              <div className="user-card__actions">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={user.is_super_admin}
                    disabled={busy || !user.is_active}
                    onChange={(e) => void setSuperAdministrator(user, e.target.checked)}
                  />
                  Super-Admin
                </label>
                <button
                  type="button"
                  className="button-danger"
                  disabled={busy || !user.is_active}
                  onClick={() => void deactivateUser(user)}
                >
                  Benutzer deaktivieren
                </button>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
