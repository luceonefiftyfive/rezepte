import { useEffect, useState } from 'react';
import { apiFetch } from '../../api/client';
import type { HealthResponse, SystemChecksResponse } from '../../types';

export function GeneralSection() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [checks, setChecks] = useState<SystemChecksResponse | null>(null);
  const [error, setError] = useState('');

  async function loadHealth(): Promise<void> {
    setError('');
    try {
      setHealth(await apiFetch<HealthResponse>('/health'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }

  async function loadChecks(): Promise<void> {
    setError('');
    try {
      setChecks(await apiFetch<SystemChecksResponse>('/system/checks'));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }

  useEffect(() => {
    void loadHealth();
    void loadChecks();
  }, []);

  return (
    <section aria-labelledby="general-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">General</p>
          <h2 id="general-heading">System status</h2>
        </div>
        <div className="button-row">
          <button type="button" onClick={() => void loadHealth()}>
            Check API
          </button>
          <button type="button" onClick={() => void loadChecks()}>
            Check services
          </button>
        </div>
      </div>

      {error && <div className="card error">{error}</div>}

      <div className="grid">
        <div className="card">
          <h3>API health</h3>
          <pre>{JSON.stringify(health, null, 2)}</pre>
        </div>
        <div className="card">
          <h3>System checks</h3>
          <pre>{JSON.stringify(checks, null, 2)}</pre>
        </div>
      </div>

      <div className="card">
        <h3>Useful URLs</h3>
        <ul>
          <li><a href="/api/health" target="_blank" rel="noreferrer">/api/health</a></li>
          <li><a href="/api/system/checks" target="_blank" rel="noreferrer">/api/system/checks</a></li>
        </ul>
      </div>
    </section>
  );
}
