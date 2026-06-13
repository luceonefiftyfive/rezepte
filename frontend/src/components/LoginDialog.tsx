import React, { useState } from "react";

type Props = {
  open: boolean;
  onClose: () => void;
  onSuccess: (tokenResponse: any) => void;
  title?: string;
  description?: string;
};

export default function LoginDialog({ open, onClose, onSuccess, title = "Sign in", description = "Sign in to access editor features." }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  async function submit() {
    setError("");
    setLoading(true);

    try {
      const resp = await fetch("/auth/local-login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!resp.ok) {
        const t = await resp.text();
        throw new Error(t || resp.statusText);
      }

      const data = await resp.json();
      onSuccess(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div className="modal-card">
        <h3>{title}</h3>
        <p>{description}</p>

        <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
          <label>
            Username
            <input value={username} onChange={(e) => setUsername(e.target.value)} />
          </label>

          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>

          {error && <div style={{ color: "#991b1b" }}>{error}</div>}

          <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
            <button type="button" onClick={submit} disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </button>
            <button type="button" onClick={onClose} style={{ background: "#e5e7eb", color: "#111827" }}>
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
