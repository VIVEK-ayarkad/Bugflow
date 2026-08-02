import { useState } from 'react';
import { Bot, Cpu, ShieldCheck, Activity, Sparkles, Check, Lock, ArrowRight } from 'lucide-react';
import { getMe, login, register } from '../api';
import { useAuth } from '../AuthContext';
import ThemeToggle from './ThemeToggle';

export default function AuthPage() {
  const { loginSuccess } = useAuth();
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('reporter');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'register') {
        const res = await register({ email, username, password, role });
        loginSuccess(res.access_token, res.user);
      } else {
        const res = await login(email, password);
        localStorage.setItem('token', res.access_token);
        const user = await getMe();
        loginSuccess(res.access_token, user);
      }
    } catch (err) {
      setError(typeof err.message === 'string' ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div style={{ position: 'absolute', top: '1.5rem', right: '1.5rem', zIndex: 100 }}>
        <ThemeToggle />
      </div>
      <div className="auth-shell">
        <section className="auth-brand">
          <div>
            <h2 style={{ fontSize: '2rem', lineHeight: '1.2', fontWeight: '800', marginBottom: '0.75rem' }}>
              Centralized Defect & Sprint Intelligence
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', lineHeight: '1.6', marginBottom: '1.5rem' }}>
              Modern bug tracking platform built with automated code diagnostics, predictive severity scoring, and real-time workload telemetry.
            </p>

            <ul className="feature-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <li className="feature-item" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <div className="feature-icon" style={{ background: 'rgba(99, 102, 241, 0.2)', padding: '0.35rem', borderRadius: '6px', color: '#818cf8' }}>
                  <ShieldCheck size={16} />
                </div>
                <span>Role-Based Access Control (RBAC System)</span>
              </li>
              <li className="feature-item" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <div className="feature-icon" style={{ background: 'rgba(99, 102, 241, 0.2)', padding: '0.35rem', borderRadius: '6px', color: '#818cf8' }}>
                  <Activity size={16} />
                </div>
                <span>Real-Time Workload & Defect Telemetry</span>
              </li>
              <li className="feature-item" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <div className="feature-icon" style={{ background: 'rgba(99, 102, 241, 0.2)', padding: '0.35rem', borderRadius: '6px', color: '#818cf8' }}>
                  <Cpu size={16} />
                </div>
                <span>Sprint Board, File Attachments & Audit Trail</span>
              </li>
              <li className="feature-item" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <div className="feature-icon" style={{ background: 'rgba(99, 102, 241, 0.2)', padding: '0.35rem', borderRadius: '6px', color: '#818cf8' }}>
                  <Sparkles size={16} />
                </div>
                <span>AI Productivity Suite: Code Doctor, Severity Predictor & Duplicate Scanner</span>
              </li>
            </ul>
          </div>

          <div style={{ marginTop: '2.5rem', fontSize: '0.8rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Lock size={14} color="#64748b" />
            <span>JWT Encrypted & Secure Defect Management</span>
          </div>
        </section>

        <div className="auth-card card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.66rem', marginBottom: '0.2rem' }}>
            <div style={{ width: '38px', height: '38px', borderRadius: '10px', background: 'linear-gradient(135deg, #6366f1, #a855f7)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
              <Bot size={22} />
            </div>
            <div>
              <h1 style={{ fontSize: '1.4rem', margin: 0 }}>BugFlow</h1>
            </div>
          </div>
          <p className="subtitle">Track software defects & sprint progress with AI intelligence.</p>

          <div className="auth-tabs">
            <button
              type="button"
              className={mode === 'login' ? 'active' : ''}
              onClick={() => {
                setMode('login');
                setError('');
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              className={mode === 'register' ? 'active' : ''}
              onClick={() => {
                setMode('register');
                setError('');
              }}
            >
              Create Account
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="email">Email Address</label>
              <input
                id="email"
                type="email"
                value={email}
                placeholder="developer@company.com"
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            {mode === 'register' && (
              <>
                <div className="form-group">
                  <label htmlFor="username">Username</label>
                  <input
                    id="username"
                    type="text"
                    value={username}
                    placeholder="alex_dev"
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    minLength={3}
                    autoComplete="username"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="role">Account Role</label>
                  <select id="role" value={role} onChange={(e) => setRole(e.target.value)}>
                    <option value="admin">Admin</option>
                    <option value="project_manager">Project Manager</option>
                    <option value="developer">Developer</option>
                    <option value="qa_tester">QA Tester</option>
                    <option value="reporter">Reporter</option>
                  </select>
                </div>
              </>
            )}

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                placeholder="••••••••••••"
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
            </div>

            {error && (
              <div className="error" style={{ marginBottom: '1.25rem' }}>
                {error}
              </div>
            )}

            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }} disabled={loading}>
              {loading ? 'Processing...' : mode === 'login' ? 'Sign In to BugFlow' : 'Create Account'}
              <ArrowRight size={16} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
