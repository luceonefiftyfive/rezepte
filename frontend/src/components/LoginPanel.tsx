import { FormEvent, useState } from 'react';
import { useAuth } from '../auth/AuthContext';

export function LoginPanel() {
  const { login } = useAuth();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setError('');

    try {
      await login(username, password);
      setPassword('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card auth-panel">
      <div className="auth-panel__header">
        <div>
          <p className="eyebrow">Authentication</p>
          <h2>Login</h2>
        </div>
        <span className="auth-token">Not signed in</span>
      </div>

      {error && <div className="auth-error">{error}</div>}

      <form onSubmit={handleSubmit} className="auth-form auth-form--login">
        <label>
          Username
          <input value={username} onChange={(event) => setUsername(event.target.value)} required />
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
