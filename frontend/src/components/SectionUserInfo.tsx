import { useState } from 'react';
import { useAuth } from '../auth/AuthContext';

type AccountSettingsTarget = 'profile' | 'password';

interface SectionUserInfoProps {
  onOpenAccountSettings: (target: AccountSettingsTarget) => void;
}

export function SectionUserInfo({ onOpenAccountSettings }: SectionUserInfoProps) {
  const { user, logout, mayManageUsers } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  if (!user) {
    return null;
  }

  function closeMenu(): void {
    setMenuOpen(false);
  }

  function openAccountSettings(target: AccountSettingsTarget): void {
    onOpenAccountSettings(target);
    closeMenu();
  }

  return (
    <div
      className="section-user"
      onMouseEnter={() => setMenuOpen(true)}
      onMouseLeave={closeMenu}
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          closeMenu();
        }
      }}
    >
      <button
        type="button"
        className="section-user-button"
        aria-expanded={menuOpen}
        aria-controls="section-user-menu"
        onClick={() => setMenuOpen(true)}
      >
        <span>
          {user.first_name} {user.last_name}
        </span>
        <span className="muted">@{user.username}</span>
      </button>
      {menuOpen && (
        <div id="section-user-menu" className="section-user-menu" role="menu">
          <span className="auth-token">
            {user.is_super_admin ? 'Super-Admin' : mayManageUsers ? 'Administrator' : 'Benutzer'}
          </span>
          <button type="button" role="menuitem" onClick={() => openAccountSettings('profile')}>
            Einstellungen
          </button>
          <button type="button" role="menuitem" onClick={() => openAccountSettings('password')}>
            Passwort ändern
          </button>
          <button
            type="button"
            role="menuitem"
            className="section-user-logout"
            onClick={() => {
              logout();
              closeMenu();
            }}
          >
            Abmelden
          </button>
        </div>
      )}
    </div>
  );
}
