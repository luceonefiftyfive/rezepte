import { useAuth } from '../auth/AuthContext';
import { useState } from 'react';

export function SectionUserInfo() {
  const { user, logout, mayManageUsers, registerPasskey } = useAuth();
  const [isRegisteringPasskey, setIsRegisteringPasskey] = useState(false);
  const [passkeyMessage, setPasskeyMessage] = useState('');

  if (!user) {
    return null;
  }

  async function handleRegisterPasskey(): Promise<void> {
    setIsRegisteringPasskey(true);
    setPasskeyMessage('');

    try {
      await registerPasskey('Standard Passkey');
      setPasskeyMessage('Passkey erfolgreich eingerichtet.');
    } catch (error) {
      setPasskeyMessage(
        error instanceof Error ? error.message : 'Passkey konnte nicht eingerichtet werden.',
      );
    } finally {
      setIsRegisteringPasskey(false);
    }
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
      <button
        type="button"
        className="button-secondary"
        onClick={() => void handleRegisterPasskey()}
        disabled={isRegisteringPasskey}
      >
        {isRegisteringPasskey ? 'Passkey wird eingerichtet …' : 'Passkey einrichten'}
      </button>
      <button type="button" className="button-secondary" onClick={logout}>
        Abmelden
      </button>
      {passkeyMessage && <div className="auth-passkey-message">{passkeyMessage}</div>}
    </div>
  );
}
