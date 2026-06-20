import { useEffect, useState } from 'react';

type User = {
  username: string;
};

export default function AuthButton() {
  const [user, setUser] = useState<User | null>(null);
  const [showLogin, setShowLogin] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  async function loadUser() {
    const res = await fetch('/api/auth/me', {
      credentials: 'include',
    });

    if (res.ok) {
      setUser(await res.json());
    } else {
      setUser(null);
    }
  }

  useEffect(() => {
    loadUser();
  }, []);

  async function login() {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      alert('Login fehlgeschlagen');
      return;
    }

    setShowLogin(false);
    setUsername('');
    setPassword('');
    await loadUser();
  }

  async function logout() {
    await fetch('/api/auth/logout', {
      method: 'POST',
      credentials: 'include',
    });

    setUser(null);
  }

  if (user) {
    return <button onClick={logout}>Abmelden</button>;
  }

  return (
    <>
      <button onClick={() => setShowLogin(true)}>Anmelden</button>

      {showLogin && (
        <div className="login-backdrop">
          <div className="login-dialog">
            <h2>Anmelden</h2>

            <input
              type="text"
              placeholder="Benutzername"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />

            <input
              type="password"
              placeholder="Passwort"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            <div>
              <button onClick={login}>Einloggen</button>
              <button onClick={() => setShowLogin(false)}>Abbrechen</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
