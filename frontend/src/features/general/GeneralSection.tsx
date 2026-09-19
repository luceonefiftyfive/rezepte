import { FormEvent, useEffect, useRef, useState } from 'react';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import { SectionUserInfo } from '../../components/SectionUserInfo';
import type {
  HealthResponse,
  RootResponse,
  SystemChecksResponse,
  SystemVersionResponse,
  UserPublic,
} from '../../types';

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`status-badge ${ok ? 'status-badge--ok' : 'status-badge--error'}`}>
      {label}
    </span>
  );
}

type AccessResult = { message: string; username: string };

interface GeneralSectionProps {
  accountSettingsTarget: 'profile' | 'password';
  accountSettingsRequestVersion: number;
  onOpenAccountSettings: (target: 'profile' | 'password') => void;
}

export function GeneralSection({
  accountSettingsTarget,
  accountSettingsRequestVersion,
  onOpenAccountSettings,
}: GeneralSectionProps) {
  const { token, isAuthenticated, logout, mayManageUsers, refreshUser, user } = useAuth();
  const [root, setRoot] = useState<RootResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [checks, setChecks] = useState<SystemChecksResponse | null>(null);
  const [systemVersion, setSystemVersion] = useState<SystemVersionResponse | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [accessResult, setAccessResult] = useState<AccessResult | null>(null);
  const [profileDraft, setProfileDraft] = useState({ firstName: '', lastName: '', email: '' });
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordConfirmation, setPasswordConfirmation] = useState('');
  const [profileError, setProfileError] = useState('');
  const [profileStatus, setProfileStatus] = useState('');
  const [profileBusy, setProfileBusy] = useState(false);
  const accountSettingsRef = useRef<HTMLDivElement>(null);
  const firstNameInputRef = useRef<HTMLInputElement>(null);
  const currentPasswordInputRef = useRef<HTMLInputElement>(null);

  async function loadStatus(): Promise<void> {
    setBusy(true);
    setError('');
    try {
      const [rootResult, healthResult, checkResult, versionResult] = await Promise.all([
        apiFetch<RootResponse>('/'),
        apiFetch<HealthResponse>('/health'),
        apiFetch<SystemChecksResponse>('/system/checks'),
        apiFetch<SystemVersionResponse>('/system/version'),
      ]);
      setRoot(rootResult);
      setHealth(healthResult);
      setChecks(checkResult);
      setSystemVersion(versionResult);
      setLastUpdated(new Date().toLocaleString('de-DE'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  async function testAccess(path: string): Promise<void> {
    setBusy(true);
    setError('');
    setAccessResult(null);
    try {
      setAccessResult(await apiFetch<AccessResult>(path, {}, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void loadStatus();
  }, []);

  useEffect(() => {
    if (!user) return;
    setProfileDraft({
      firstName: user.first_name,
      lastName: user.last_name,
      email: user.email,
    });
  }, [user]);

  useEffect(() => {
    if (accountSettingsRequestVersion === 0) return;
    accountSettingsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    const target =
      accountSettingsTarget === 'password'
        ? currentPasswordInputRef.current
        : firstNameInputRef.current;
    window.requestAnimationFrame(() => target?.focus());
  }, [accountSettingsRequestVersion, accountSettingsTarget]);

  async function updateProfile(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setProfileBusy(true);
    setProfileError('');
    setProfileStatus('');
    try {
      await apiFetch<UserPublic>(
        '/users/me',
        {
          method: 'PATCH',
          body: JSON.stringify({
            first_name: profileDraft.firstName.trim(),
            last_name: profileDraft.lastName.trim(),
            email: profileDraft.email.trim(),
          }),
        },
        token,
      );
      await refreshUser();
      setProfileStatus('Persönliche Daten wurden gespeichert.');
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setProfileBusy(false);
    }
  }

  async function updatePassword(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setProfileError('');
    setProfileStatus('');
    if (newPassword !== passwordConfirmation) {
      setProfileError('Die neuen Passwörter stimmen nicht überein.');
      return;
    }

    setProfileBusy(true);
    try {
      await apiFetch<void>(
        '/users/me/password',
        {
          method: 'PATCH',
          body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
          }),
        },
        token,
      );
      logout('Passwort geändert. Bitte melden Sie sich mit dem neuen Passwort an.');
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setProfileBusy(false);
    }
  }

  return (
    <section aria-labelledby="general-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Diagnose</p>
          <h2 id="general-heading">Systemstatus</h2>
        </div>
        <div className="section-heading-actions">
          <SectionUserInfo onOpenAccountSettings={onOpenAccountSettings} />
          <button type="button" onClick={() => void loadStatus()} disabled={busy}>
            {busy ? 'Prüfung läuft …' : 'Erneut prüfen'}
          </button>
        </div>
      </div>

      {error && (
        <div className="card error" role="alert">
          {error}
        </div>
      )}

      {isAuthenticated && user && (
        <div ref={accountSettingsRef} className="card auth-panel">
          <h3>Mein Konto</h3>
          {profileError && (
            <div className="auth-error" role="alert">
              {profileError}
            </div>
          )}
          {profileStatus && (
            <div className="auth-status" role="status">
              {profileStatus}
            </div>
          )}
          <form className="auth-form" onSubmit={updateProfile}>
            <label>
              Vorname
              <input
                ref={firstNameInputRef}
                autoComplete="given-name"
                value={profileDraft.firstName}
                onChange={(event) =>
                  setProfileDraft((current) => ({ ...current, firstName: event.target.value }))
                }
                required
              />
            </label>
            <label>
              Nachname
              <input
                autoComplete="family-name"
                value={profileDraft.lastName}
                onChange={(event) =>
                  setProfileDraft((current) => ({ ...current, lastName: event.target.value }))
                }
                required
              />
            </label>
            <label>
              E-Mail
              <input
                type="email"
                autoComplete="email"
                value={profileDraft.email}
                onChange={(event) =>
                  setProfileDraft((current) => ({ ...current, email: event.target.value }))
                }
                required
              />
            </label>
            <div className="button-row">
              <button type="submit" disabled={profileBusy}>
                {profileBusy ? 'Speichern …' : 'Persönliche Daten speichern'}
              </button>
            </div>
          </form>
          <form className="auth-form" onSubmit={updatePassword}>
            <h4>Passwort ändern</h4>
            <label>
              Aktuelles Passwort
              <input
                ref={currentPasswordInputRef}
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                required
              />
            </label>
            <label>
              Neues Passwort
              <input
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
              />
            </label>
            <label>
              Neues Passwort wiederholen
              <input
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={passwordConfirmation}
                onChange={(event) => setPasswordConfirmation(event.target.value)}
                required
              />
            </label>
            <div className="button-row">
              <button type="submit" disabled={profileBusy}>
                {profileBusy ? 'Passwort wird geändert …' : 'Passwort ändern'}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="status-grid">
        <article className="card status-card">
          <div className="status-card__title">
            <h3>API</h3>
            <StatusBadge
              ok={health?.status === 'ok'}
              label={health?.status === 'ok' ? 'Erreichbar' : 'Unbekannt'}
            />
          </div>
          <dl>
            <dt>Dienst</dt>
            <dd>{health?.service ?? root?.service ?? '–'}</dd>
            <dt>Modus</dt>
            <dd>{health?.mode ?? '–'}</dd>
            <dt>Python</dt>
            <dd>{root?.python ?? '–'}</dd>
          </dl>
        </article>
        <article className="card status-card">
          <div className="status-card__title">
            <h3>MongoDB</h3>
            <StatusBadge
              ok={Boolean(checks?.mongo_db.ok)}
              label={checks?.mongo_db.ok ? 'Verbunden' : 'Nicht verbunden'}
            />
          </div>
          {checks?.mongo_db.error && <p className="technical-error">{checks.mongo_db.error}</p>}
        </article>
        <article className="card status-card">
          <div className="status-card__title">
            <h3>S3-Speicher</h3>
            <StatusBadge
              ok={Boolean(checks?.s3.ok)}
              label={checks?.s3.ok ? 'Verbunden' : 'Nicht verbunden'}
            />
          </div>
          <dl>
            <dt>Bucket</dt>
            <dd>{checks?.s3.bucket ?? '–'}</dd>
            <dt>Endpunkt</dt>
            <dd>{checks?.s3.endpoint ?? '–'}</dd>
          </dl>
          {checks?.s3.error && <p className="technical-error">{checks.s3.error}</p>}
        </article>
        <article className="card status-card">
          <div className="status-card__title">
            <h3>Version</h3>
            <StatusBadge
              ok={Boolean(systemVersion)}
              label={systemVersion ? 'Bekannt' : 'Unbekannt'}
            />
          </div>
          <dl>
            <dt>Release</dt>
            <dd>{systemVersion?.version ?? '–'}</dd>
            <dt>Git-Hash</dt>
            <dd>{systemVersion?.git_hash ?? '–'}</dd>
            <dt>Aktualisiert</dt>
            <dd>{lastUpdated ?? '–'}</dd>
          </dl>
        </article>
      </div>

      {isAuthenticated && (
        <div className="card">
          <h3>Berechtigungen prüfen</h3>
          <p className="muted">
            Testet die geschützten Diagnose-Endpunkte mit dem aktuellen Zugriffstoken.
          </p>
          <div className="button-row">
            <button type="button" disabled={busy} onClick={() => void testAccess('/test-access')}>
              Anmeldung prüfen
            </button>
            {mayManageUsers && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void testAccess('/test-admin-access')}
              >
                Administrator prüfen
              </button>
            )}
            {user?.is_super_admin && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void testAccess('/test-super-admin-access')}
              >
                Super-Admin prüfen
              </button>
            )}
          </div>
          {accessResult && (
            <div className="auth-status access-result">
              {accessResult.message} – {accessResult.username}
            </div>
          )}
        </div>
      )}

      <div className="card">
        <h3>API-Endpunkte</h3>
        <div className="endpoint-list">
          <a href="/api/" target="_blank" rel="noreferrer">
            /api/
          </a>
          <a href="/api/health" target="_blank" rel="noreferrer">
            /api/health
          </a>
          <a href="/api/system/version" target="_blank" rel="noreferrer">
            /api/system/version
          </a>
          <a href="/api/system/checks" target="_blank" rel="noreferrer">
            /api/system/checks
          </a>
          <a href="/api/docs" target="_blank" rel="noreferrer">
            /api/docs
          </a>
        </div>
      </div>
    </section>
  );
}
