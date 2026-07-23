import { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { fetchProviders } from '../services/auth';
import type { AuthProviderInfo } from '../types';

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const location = useLocation();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [providers, setProviders] = useState<AuthProviderInfo[]>([]);

  useEffect(() => {
    fetchProviders()
      .then((res) => setProviders(res.providers))
      .catch(() => {
        // Provider list is informational; failure shouldn't block the form.
      });
  }, []);

  const from = (location.state as { from?: string } | null)?.from || '/';

  if (isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(username, password);
    } catch (err: unknown) {
      const e = err as {
        response?: { data?: { detail?: string }; status?: number };
        message?: string;
      };
      if (!e.response) {
        setError(
          'Could not reach the server. Make sure the backend is running ' +
            '(check `docker compose logs backend`).',
        );
      } else if (e.response.data?.detail) {
        setError(e.response.data.detail);
      } else {
        setError(`Login failed (HTTP ${e.response.status ?? '?'}).`);
      }
    } finally {
      setSubmitting(false);
    }
  }

  const oauthProviders = providers.filter((p) => !p.supports_password_login);

  return (
    <div className="login-shell">
      <div className="login-card">
        <h1>Meeting Assistant</h1>
        <p className="tagline">Sign in to manage and process your meeting recordings.</p>

        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>
          <button type="submit" className="submit" disabled={submitting}>
            {submitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <div className="muted" style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
          Default credentials: <code>admin</code> / <code>admin</code>
        </div>

        {oauthProviders.length > 0 && (
          <>
            <div className="divider">or</div>
            {oauthProviders.map((p) => (
              <button
                key={p.name}
                type="button"
                className="oauth-btn"
                disabled={!p.enabled}
                title={p.enabled ? '' : 'Configure OAuth client id in .env to enable'}
              >
                {p.label}
                {!p.enabled && (
                  <span className="muted" style={{ fontSize: '0.7rem' }}>
                    (placeholder)
                  </span>
                )}
              </button>
            ))}
            <p className="oauth-note">
              Plug in OAuth/SSO by implementing a new <code>AuthProvider</code> in{' '}
              <code>backend/app/auth/</code>.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
