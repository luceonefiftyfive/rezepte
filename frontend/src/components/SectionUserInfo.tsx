import { useAuth } from '../auth/AuthContext';

type AccountSettingsTarget = 'profile' | 'password';

interface SectionUserInfoProps {
  onOpenAccountSettings: (target: AccountSettingsTarget) => void;
}

export function SectionUserInfo({ onOpenAccountSettings }: SectionUserInfoProps) {
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
      <button
        type="button"
        className="button-secondary"
        onClick={() => onOpenAccountSettings('profile')}
      >
        Einstellungen
      </button>
      <button
        type="button"
        className="button-secondary"
        onClick={() => onOpenAccountSettings('password')}
      >
        Passwort ändern
      </button>
      <span className="auth-token">
        {user.is_super_admin ? 'Super-Admin' : mayManageUsers ? 'Administrator' : 'Benutzer'}
      </span>
      <button type="button" className="button-secondary" onClick={() => logout()}>
        Abmelden
      </button>
    </div>
  );
}
