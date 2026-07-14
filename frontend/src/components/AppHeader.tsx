import { useAuth } from '../auth/AuthContext';

export function AppHeader() {
  const { user, logout, mayManageUsers } = useAuth();

  return (
    <header className="hero">
      <div>
        <p className="eyebrow">Familienrezepte</p>
        <h1>Unsere Rezeptsammlung</h1>
        <p>Rezepte verwalten, Bilder testen und Benutzerrechte steuern.</p>
      </div>

      {user && (
        <div className="header-user">
          <div>
            <strong>{user.first_name} {user.last_name}</strong>
            <div className="muted">@{user.username}</div>
          </div>
          <span className="auth-token">
            {user.is_super_admin ? 'Super-Admin' : mayManageUsers ? 'Administrator' : 'Benutzer'}
          </span>
          <button type="button" className="button-secondary" onClick={logout}>Abmelden</button>
        </div>
      )}
    </header>
  );
}
