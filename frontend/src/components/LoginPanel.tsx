import { FormEvent, useState } from 'react';
import { useAuth } from '../auth/AuthContext';

export function LoginPanel() {
  const { login, loginWithPasskey } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [busyPasskey, setBusyPasskey] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await login(username.trim(), password);
      setPassword('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  async function handlePasskeyLogin(): Promise<void> {
    if (!username.trim()) {
      setError('Bitte Benutzernamen für Passkey-Anmeldung eingeben.');
      return;
    }

    setBusyPasskey(true);
    setError('');
    try {
      await loginWithPasskey(username.trim());
      setPassword('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusyPasskey(false);
    }
  }

  return (
    <section className="card auth-panel">
      <div className="auth-panel__header">
        <div>
          <p className="eyebrow">Geschützter Bereich</p>
          <h2>Anmelden</h2>
        </div>
        <span className="auth-token">Nicht angemeldet</span>
      </div>
      {error && (
        <div className="auth-error" role="alert">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit} className="auth-form auth-form--login">
        <label>
          Benutzername
          <input
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </label>
        <label>
          Passwort
          <input
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            required
          />
        </label>
        <div className="button-row auth-form-actions">
          <button type="submit" disabled={busy || busyPasskey}>
            {busy ? 'Anmeldung läuft …' : 'Anmelden'}
          </button>
          <button
            type="button"
            className="button-secondary"
            disabled={busy || busyPasskey}
            onClick={() => void handlePasskeyLogin()}
          >
            {busyPasskey ? 'Passkey läuft …' : 'Mit Passkey anmelden'}
          </button>
        </div>
      </form>
    </section>
  );
}
