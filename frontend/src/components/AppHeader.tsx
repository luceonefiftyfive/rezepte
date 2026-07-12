import { useAuth } from '../auth/AuthContext';

export function AppHeader() {
  const { user, logout, mayManageUsers } = useAuth();

  return (
    <header className="hero">
      <div>
        <p className="eyebrow">Familienrezepte</p>
        <h1>Recipe application</h1>
        <p>Public information, protected recipe entry and role-based user administration.</p>
      </div>

      {user && (
        <div className="header-user">
          <div>
            <strong>
              {user.first_name} {user.last_name}
            </strong>
            <div className="muted">@{user.username}</div>
          </div>
          <span className="auth-token">
            {user.is_super_admin ? 'Super-admin' : mayManageUsers ? 'Admin' : 'User'}
          </span>
          <button type="button" className="button-secondary" onClick={logout}>
            Logout
          </button>
        </div>
      )}
    </header>
  );
}
