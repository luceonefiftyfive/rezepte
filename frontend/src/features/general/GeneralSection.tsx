import { useEffect, useState } from 'react';
import { apiFetch } from '../../api/client';
import { useAuth } from '../../auth/AuthContext';
import type { HealthResponse, RootResponse, SystemChecksResponse } from '../../types';

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return <span className={`status-badge ${ok ? 'status-badge--ok' : 'status-badge--error'}`}>{label}</span>;
}

type AccessResult = { message: string; username: string };

export function GeneralSection() {
  const { token, isAuthenticated, mayManageUsers, user } = useAuth();
  const [root, setRoot] = useState<RootResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [checks, setChecks] = useState<SystemChecksResponse | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [accessResult, setAccessResult] = useState<AccessResult | null>(null);

  async function loadStatus(): Promise<void> {
    setBusy(true);
    setError('');
    try {
      const [rootResult, healthResult, checkResult] = await Promise.all([
        apiFetch<RootResponse>('/'),
        apiFetch<HealthResponse>('/health'),
        apiFetch<SystemChecksResponse>('/system/checks'),
      ]);
      setRoot(rootResult);
      setHealth(healthResult);
      setChecks(checkResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally {
      setBusy(false);
    }
  }

  async function testAccess(path: string): Promise<void> {
    setBusy(true); setError(''); setAccessResult(null);
    try {
      setAccessResult(await apiFetch<AccessResult>(path, {}, token));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
    } finally { setBusy(false); }
  }

  useEffect(() => { void loadStatus(); }, []);

  return (
    <section aria-labelledby="general-heading">
      <div className="section-heading">
        <div><p className="eyebrow">Diagnose</p><h2 id="general-heading">Systemstatus</h2></div>
        <button type="button" onClick={() => void loadStatus()} disabled={busy}>{busy ? 'Prüfung läuft …' : 'Erneut prüfen'}</button>
      </div>

      {error && <div className="card error" role="alert">{error}</div>}

      <div className="status-grid">
        <article className="card status-card">
          <div className="status-card__title"><h3>API</h3><StatusBadge ok={health?.status === 'ok'} label={health?.status === 'ok' ? 'Erreichbar' : 'Unbekannt'} /></div>
          <dl><dt>Dienst</dt><dd>{health?.service ?? root?.service ?? '–'}</dd><dt>Modus</dt><dd>{health?.mode ?? '–'}</dd><dt>Python</dt><dd>{root?.python ?? '–'}</dd></dl>
        </article>
        <article className="card status-card">
          <div className="status-card__title"><h3>MongoDB</h3><StatusBadge ok={Boolean(checks?.mongo_db.ok)} label={checks?.mongo_db.ok ? 'Verbunden' : 'Nicht verbunden'} /></div>
          {checks?.mongo_db.error && <p className="technical-error">{checks.mongo_db.error}</p>}
        </article>
        <article className="card status-card">
          <div className="status-card__title"><h3>S3-Speicher</h3><StatusBadge ok={Boolean(checks?.s3.ok)} label={checks?.s3.ok ? 'Verbunden' : 'Nicht verbunden'} /></div>
          <dl><dt>Bucket</dt><dd>{checks?.s3.bucket ?? '–'}</dd><dt>Endpunkt</dt><dd>{checks?.s3.endpoint ?? '–'}</dd></dl>
          {checks?.s3.error && <p className="technical-error">{checks.s3.error}</p>}
        </article>
      </div>

      {isAuthenticated && (
        <div className="card">
          <h3>Berechtigungen prüfen</h3>
          <p className="muted">Testet die geschützten Diagnose-Endpunkte mit dem aktuellen Zugriffstoken.</p>
          <div className="button-row">
            <button type="button" disabled={busy} onClick={() => void testAccess('/test-access')}>Anmeldung prüfen</button>
            {mayManageUsers && <button type="button" disabled={busy} onClick={() => void testAccess('/test-admin-access')}>Administrator prüfen</button>}
            {user?.is_super_admin && <button type="button" disabled={busy} onClick={() => void testAccess('/test-super-admin-access')}>Super-Admin prüfen</button>}
          </div>
          {accessResult && <div className="auth-status access-result">{accessResult.message} – {accessResult.username}</div>}
        </div>
      )}

      <div className="card">
        <h3>API-Endpunkte</h3>
        <div className="endpoint-list">
          <a href="/api/" target="_blank" rel="noreferrer">/api/</a>
          <a href="/api/health" target="_blank" rel="noreferrer">/api/health</a>
          <a href="/api/system/checks" target="_blank" rel="noreferrer">/api/system/checks</a>
          <a href="/api/docs" target="_blank" rel="noreferrer">/api/docs</a>
        </div>
      </div>
    </section>
  );
}
