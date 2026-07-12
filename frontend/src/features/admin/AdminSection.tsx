import { FormEvent, useEffect, useState } from 'react';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import type { GroupRole, Role, UserPublic } from '../../types';

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
  username: '', password: '', first_name: '', last_name: '', email: '',
  group_id: 'recipes', role: 'reader', is_super_admin: false,
};

export function AdminSection() {
  const { token, user: currentUser, refreshUser } = useAuth();
  const [users, setUsers] = useState<UserPublic[]>([]);
  const [newUser, setNewUser] = useState<NewUserForm>(EMPTY_NEW_USER);
  const [groupDrafts, setGroupDrafts] = useState<Record<string, GroupRole[]>>({});
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
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }

  useEffect(() => { void loadUsers(); }, [token]);

  async function createUser(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setBusy(true); setError(''); setStatus('');
    try {
      const groups = newUser.group_id.trim()
        ? [{ group_id: newUser.group_id.trim(), role: newUser.role }]
        : [];
      await apiFetch<UserPublic>('/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: newUser.username.trim(), password: newUser.password,
          first_name: newUser.first_name.trim(), last_name: newUser.last_name.trim(),
          email: newUser.email.trim(), groups,
          is_super_admin: currentUser?.is_super_admin ? newUser.is_super_admin : false,
        }),
      }, token);
      setStatus(`User ${newUser.username} created`);
      setNewUser(EMPTY_NEW_USER);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally { setBusy(false); }
  }

  function updateGroup(userId: string, index: number, patch: Partial<GroupRole>): void {
    setGroupDrafts((current) => ({
      ...current,
      [userId]: (current[userId] ?? []).map((group, i) => i === index ? { ...group, ...patch } : group),
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
      ...group, group_id: group.group_id.trim(),
    }));
    if (groups.some((group) => !group.group_id)) {
      setError('Every group must have a group ID.');
      return;
    }
    setBusy(true); setError('');
    try {
      await apiFetch<UserPublic>(`/users/${user.id}/groups`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ groups }),
      }, token);
      setStatus(`Groups updated for ${user.username}`);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally { setBusy(false); }
  }

  async function setSuperAdmin(user: UserPublic, isSuperAdmin: boolean): Promise<void> {
    setBusy(true); setError('');
    try {
      await apiFetch<UserPublic>(`/users/${user.id}/super-admin`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_super_admin: isSuperAdmin }),
      }, token);
      await loadUsers();
      if (user.id === currentUser?.id) await refreshUser();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally { setBusy(false); }
  }

  async function deactivateUser(user: UserPublic): Promise<void> {
    if (!window.confirm(`Deactivate user "${user.username}"?`)) return;
    setBusy(true); setError('');
    try {
      await apiFetch<{ deleted: boolean }>(`/users/${user.id}`, { method: 'DELETE' }, token);
      setStatus(`${user.username} was deactivated`);
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally { setBusy(false); }
  }

  return (
    <section aria-labelledby="admin-heading">
      <div className="section-heading">
        <div><p className="eyebrow">Restricted area</p><h2 id="admin-heading">User administration</h2></div>
        <button type="button" onClick={() => void loadUsers()} disabled={busy}>Reload users</button>
      </div>
      {status && <div className="auth-status">{status}</div>}
      {error && <div className="auth-error">{error}</div>}

      <form onSubmit={createUser} className="card user-create-form">
        <h3>Create user</h3>
        <div className="form-grid">
          <label>Username<input value={newUser.username} onChange={(e) => setNewUser({...newUser, username:e.target.value})} required /></label>
          <label>Password<input type="password" minLength={8} value={newUser.password} onChange={(e) => setNewUser({...newUser, password:e.target.value})} required /></label>
          <label>First name<input value={newUser.first_name} onChange={(e) => setNewUser({...newUser, first_name:e.target.value})} required /></label>
          <label>Last name<input value={newUser.last_name} onChange={(e) => setNewUser({...newUser, last_name:e.target.value})} required /></label>
          <label>Email<input type="email" value={newUser.email} onChange={(e) => setNewUser({...newUser, email:e.target.value})} required /></label>
          <label>Group ID<input value={newUser.group_id} onChange={(e) => setNewUser({...newUser, group_id:e.target.value})} /></label>
          <label>Role<select value={newUser.role} onChange={(e) => setNewUser({...newUser, role:e.target.value as Role})}><option value="reader">Reader</option><option value="author">Author</option><option value="admin">Admin</option></select></label>
          {currentUser?.is_super_admin && <label className="checkbox-label"><input type="checkbox" checked={newUser.is_super_admin} onChange={(e) => setNewUser({...newUser, is_super_admin:e.target.checked})} />Super-admin</label>}
        </div>
        <button type="submit" disabled={busy}>Create user</button>
      </form>

      <div className="user-list">
        {users.map((user) => (
          <article className={`card user-card ${!user.is_active ? 'user-card--inactive' : ''}`} key={user.id}>
            <div className="user-card__header"><div><h3>{user.first_name} {user.last_name}</h3><p className="muted">@{user.username} · {user.email}</p></div><div className="badge-row">{user.is_super_admin && <span className="badge">Super-admin</span>}{!user.is_active && <span className="badge badge--danger">Inactive</span>}</div></div>
            <div className="group-editor">
              <strong>Group roles</strong>
              {(groupDrafts[user.id] ?? []).map((group, index) => <div className="group-row" key={`${user.id}-${index}`}><input value={group.group_id} onChange={(e) => updateGroup(user.id,index,{group_id:e.target.value})} /><select value={group.role} onChange={(e) => updateGroup(user.id,index,{role:e.target.value as Role})}><option value="reader">Reader</option><option value="author">Author</option><option value="admin">Admin</option></select><button type="button" className="button-danger button-small" onClick={() => removeGroup(user.id,index)}>Remove</button></div>)}
              <div className="button-row"><button type="button" className="button-secondary button-small" onClick={() => addGroup(user.id)}>Add group</button><button type="button" className="button-small" disabled={busy || !user.is_active} onClick={() => void saveGroups(user)}>Save groups</button></div>
            </div>
            {currentUser?.is_super_admin && <div className="user-card__actions"><label className="checkbox-label"><input type="checkbox" checked={user.is_super_admin} disabled={busy || !user.is_active} onChange={(e) => void setSuperAdmin(user,e.target.checked)} />Super-admin</label><button type="button" className="button-danger" disabled={busy || !user.is_active} onClick={() => void deactivateUser(user)}>Deactivate user</button></div>}
          </article>
        ))}
      </div>
    </section>
  );
}
