import { FormEvent, useEffect, useMemo, useState } from 'react';

const API_BASE = '/api';
const TOKEN_KEY = 'rezepte-auth-token';

type Role = 'admin' | 'author' | 'reader';

type GroupRole = {
  group_id: string;
  role: Role;
};

type UserPublic = {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  email_verified: boolean;
  groups: GroupRole[];
  is_super_admin: boolean;
  is_active: boolean;
};

type TokenResponse = {
  access_token: string;
  token_type: string;
  user: UserPublic;
};

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

function readErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Unknown error';
}

async function readResponseError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string; message?: string };
    return payload.detail ?? payload.message ?? `${response.status} ${response.statusText}`;
  } catch {
    return `${response.status} ${response.statusText}`;
  }
}

export default function AuthButton() {
  const [token, setToken] = useState<string | null>(() =>
    typeof window === 'undefined' ? null : window.localStorage.getItem(TOKEN_KEY),
  );
  const [currentUser, setCurrentUser] = useState<UserPublic | null>(null);
  const [users, setUsers] = useState<UserPublic[]>([]);
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin');
  const [newUser, setNewUser] = useState<NewUserForm>(EMPTY_NEW_USER);
  const [groupDrafts, setGroupDrafts] = useState<Record<string, GroupRole[]>>({});
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const mayManageUsers = useMemo(
    () =>
      Boolean(
        currentUser?.is_super_admin || currentUser?.groups.some((group) => group.role === 'admin'),
      ),
    [currentUser],
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  }, [token]);

  useEffect(() => {
    if (token) void loadCurrentUser(token);
  }, [token]);

  useEffect(() => {
    if (token && mayManageUsers) void loadUsers(token);
    if (!mayManageUsers) setUsers([]);
  }, [token, mayManageUsers]);

  async function apiFetch<T>(
    path: string,
    options: RequestInit = {},
    authToken = token,
  ): Promise<T> {
    const headers = new Headers(options.headers);
    if (authToken) headers.set('Authorization', `Bearer ${authToken}`);

    const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (!response.ok) throw new Error(await readResponseError(response));
    return response.json() as Promise<T>;
  }

  function showError(err: unknown): void {
    setStatus('');
    setError(readErrorMessage(err));
  }

  async function loadCurrentUser(currentToken: string): Promise<void> {
    setError('');
    try {
      const user = await apiFetch<UserPublic>('/auth/me', {}, currentToken);
      setCurrentUser(user);
    } catch (err) {
      setCurrentUser(null);
      setToken(null);
      showError(err);
    }
  }

  async function loadUsers(currentToken = token): Promise<void> {
    if (!currentToken) return;
    setError('');
    try {
      const data = await apiFetch<UserPublic[]>('/users', {}, currentToken);
      setUsers(data);
      setGroupDrafts(Object.fromEntries(data.map((user) => [user.id, user.groups])));
    } catch (err) {
      showError(err);
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setError('');
    setStatus('');
    try {
      const data = await apiFetch<TokenResponse>(
        '/auth/login',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password }),
        },
        null,
      );
      setToken(data.access_token);
      setCurrentUser(data.user);
      setPassword('');
      setStatus(`Login successful for ${data.user.username}`);
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  function handleLogout(): void {
    setToken(null);
    setCurrentUser(null);
    setUsers([]);
    setStatus('Logged out');
    setError('');
  }

  async function createUser(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const groups = newUser.group_id.trim()
        ? [{ group_id: newUser.group_id.trim(), role: newUser.role }]
        : [];
      await apiFetch<UserPublic>('/users', {
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
      });
      setNewUser(EMPTY_NEW_USER);
      setStatus(`User ${newUser.username} created`);
      await loadUsers();
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  function updateGroupDraft(userId: string, index: number, patch: Partial<GroupRole>): void {
    setGroupDrafts((current) => ({
      ...current,
      [userId]: (current[userId] ?? []).map((group, groupIndex) =>
        groupIndex === index ? { ...group, ...patch } : group,
      ),
    }));
  }

  function addGroupDraft(userId: string): void {
    setGroupDrafts((current) => ({
      ...current,
      [userId]: [...(current[userId] ?? []), { group_id: '', role: 'reader' }],
    }));
  }

  function removeGroupDraft(userId: string, index: number): void {
    setGroupDrafts((current) => ({
      ...current,
      [userId]: (current[userId] ?? []).filter((_, groupIndex) => groupIndex !== index),
    }));
  }

  async function saveGroups(user: UserPublic): Promise<void> {
    setBusy(true);
    setError('');
    try {
      const groups = (groupDrafts[user.id] ?? []).map((group) => ({
        ...group,
        group_id: group.group_id.trim(),
      }));
      if (groups.some((group) => !group.group_id)) {
        throw new Error('Every group must have a group ID.');
      }
      await apiFetch<UserPublic>(`/users/${user.id}/groups`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ groups }),
      });
      setStatus(`Groups updated for ${user.username}`);
      await loadUsers();
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  async function setSuperAdmin(user: UserPublic, isSuperAdmin: boolean): Promise<void> {
    setBusy(true);
    setError('');
    try {
      await apiFetch<UserPublic>(`/users/${user.id}/super-admin`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_super_admin: isSuperAdmin }),
      });
      setStatus(`${user.username} ${isSuperAdmin ? 'is now' : 'is no longer'} a super-admin`);
      await loadUsers();
      if (user.id === currentUser?.id && token) await loadCurrentUser(token);
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  async function deactivateUser(user: UserPublic): Promise<void> {
    if (!window.confirm(`Deactivate user "${user.username}"?`)) return;
    setBusy(true);
    setError('');
    try {
      await apiFetch<{ deleted: boolean }>(`/users/${user.id}`, { method: 'DELETE' });
      setStatus(`${user.username} was deactivated`);
      await loadUsers();
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  if (!currentUser) {
    return (
      <section className="auth-panel">
        <div className="auth-panel__header">
          <div>
            <p className="eyebrow">Authentication</p>
            <h2>Login</h2>
          </div>
          <div className="auth-token">Not signed in</div>
        </div>
        {status && <div className="auth-status">{status}</div>}
        {error && <div className="auth-error">{error}</div>}
        <form onSubmit={handleLogin} className="auth-form auth-form--login">
          <label>
            Username
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </label>
          <label>
            Password
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              required
            />
          </label>
          <button type="submit" disabled={busy}>
            Login
          </button>
        </form>
      </section>
    );
  }

  return (
    <section className="auth-panel">
      <div className="auth-panel__header">
        <div>
          <p className="eyebrow">Signed in</p>
          <h2>
            {currentUser.first_name} {currentUser.last_name}
          </h2>
          <p className="muted">
            @{currentUser.username} · {currentUser.email}
          </p>
        </div>
        <div className="button-row">
          <span className="auth-token">
            {currentUser.is_super_admin ? 'Super-admin' : mayManageUsers ? 'Admin' : 'User'}
          </span>
          <button type="button" className="button-secondary" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </div>

      {status && <div className="auth-status">{status}</div>}
      {error && <div className="auth-error">{error}</div>}

      {!mayManageUsers && (
        <div className="auth-card">
          <p>You do not have user-management permissions.</p>
        </div>
      )}

      {mayManageUsers && (
        <>
          <div className="admin-toolbar">
            <div>
              <h3>User management</h3>
              <p className="muted">Create users and manage their group roles.</p>
            </div>
            <button
              type="button"
              className="button-secondary"
              onClick={() => void loadUsers()}
              disabled={busy}
            >
              Reload users
            </button>
          </div>

          <form onSubmit={createUser} className="user-create-form">
            <h3>Create user</h3>
            <div className="form-grid">
              <label>
                Username
                <input
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  minLength={3}
                  required
                />
              </label>
              <label>
                Password
                <input
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  type="password"
                  minLength={8}
                  required
                />
              </label>
              <label>
                First name
                <input
                  value={newUser.first_name}
                  onChange={(e) => setNewUser({ ...newUser, first_name: e.target.value })}
                  required
                />
              </label>
              <label>
                Last name
                <input
                  value={newUser.last_name}
                  onChange={(e) => setNewUser({ ...newUser, last_name: e.target.value })}
                  required
                />
              </label>
              <label>
                Email
                <input
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  type="email"
                  required
                />
              </label>
              <label>
                Group ID
                <input
                  value={newUser.group_id}
                  onChange={(e) => setNewUser({ ...newUser, group_id: e.target.value })}
                  placeholder="recipes"
                />
              </label>
              <label>
                Role
                <select
                  value={newUser.role}
                  onChange={(e) => setNewUser({ ...newUser, role: e.target.value as Role })}
                >
                  <option value="reader">Reader</option>
                  <option value="author">Author</option>
                  <option value="admin">Admin</option>
                </select>
              </label>
              {currentUser.is_super_admin && (
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={newUser.is_super_admin}
                    onChange={(e) => setNewUser({ ...newUser, is_super_admin: e.target.checked })}
                  />
                  Create as super-admin
                </label>
              )}
            </div>
            <button type="submit" disabled={busy}>
              Create user
            </button>
          </form>

          <div className="user-list">
            {users.map((user) => (
              <article
                className={`user-card ${!user.is_active ? 'user-card--inactive' : ''}`}
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
                    {user.is_super_admin && <span className="badge">Super-admin</span>}
                    {!user.email_verified && (
                      <span className="badge badge--warning">Email unverified</span>
                    )}
                    {!user.is_active && <span className="badge badge--danger">Inactive</span>}
                  </div>
                </div>

                <div className="group-editor">
                  <strong>Group roles</strong>
                  {(groupDrafts[user.id] ?? []).map((group, index) => (
                    <div className="group-row" key={`${user.id}-${index}`}>
                      <input
                        aria-label="Group ID"
                        value={group.group_id}
                        onChange={(e) =>
                          updateGroupDraft(user.id, index, { group_id: e.target.value })
                        }
                      />
                      <select
                        aria-label="Role"
                        value={group.role}
                        onChange={(e) =>
                          updateGroupDraft(user.id, index, { role: e.target.value as Role })
                        }
                      >
                        <option value="reader">Reader</option>
                        <option value="author">Author</option>
                        <option value="admin">Admin</option>
                      </select>
                      <button
                        type="button"
                        className="button-danger button-small"
                        onClick={() => removeGroupDraft(user.id, index)}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                  <div className="button-row">
                    <button
                      type="button"
                      className="button-secondary button-small"
                      onClick={() => addGroupDraft(user.id)}
                    >
                      Add group
                    </button>
                    <button
                      type="button"
                      className="button-small"
                      onClick={() => void saveGroups(user)}
                      disabled={busy || !user.is_active}
                    >
                      Save groups
                    </button>
                  </div>
                </div>

                {currentUser.is_super_admin && (
                  <div className="user-card__actions">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={user.is_super_admin}
                        onChange={(e) => void setSuperAdmin(user, e.target.checked)}
                        disabled={busy || !user.is_active}
                      />
                      Super-admin
                    </label>
                    <button
                      type="button"
                      className="button-danger"
                      onClick={() => void deactivateUser(user)}
                      disabled={busy || !user.is_active}
                    >
                      Deactivate user
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
