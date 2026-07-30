import { useAuth } from '../auth/AuthContext';

export function SectionUserInfo() {
  const { user, logout, mayManageUsers } = useAuth();

  if (!user) {
    return null;
  }

  return (
    <div className="section-user">
      <div>
        <strong>
          {user.first_name} {user.last_name}
        </strong>
        <div className="muted">@{user.username}</div>
      </div>
      <span className="auth-token">
        {user.is_super_admin ? 'Super-Admin' : mayManageUsers ? 'Administrator' : 'Benutzer'}
      </span>
      <button type="button" className="button-secondary" onClick={logout}>
        Abmelden
      </button>
    </div>
  );
}
