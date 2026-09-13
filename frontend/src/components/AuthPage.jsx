import { useState } from 'react';
import {
  Bot,
  Zap,
  Cpu,
  Sparkles,
  Lock,
  ArrowRight,
  Eye,
  EyeOff,
  Mail,
  User,
  Shield,
  AlertCircle,
} from 'lucide-react';
import { getMe, login, register } from '../api';
import { useAuth } from '../AuthContext';
import ThemeToggle from './ThemeToggle';

export default function AuthPage() {
  const { loginSuccess } = useAuth();
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('developer');
  const [showPassword, setShowPassword] = useState(false);
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
      setError(typeof err.message === 'string' ? err.message : 'Invalid credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div style={{ position: 'absolute', top: '1.25rem', right: '1.5rem', zIndex: 100 }}>
        <ThemeToggle />
      </div>

      <div className="auth-shell">
        {/* Left Side: Brand Showcase */}
        <section className="auth-brand">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', marginBottom: '1.5rem' }}>
              <img
                src="/logo.png"
                alt="BugFlow Logo"
                style={{
                  width: '56px',
                  height: '56px',
                  objectFit: 'contain',
                  background: 'transparent',
                  display: 'block'
                }}
              />
              <h1 style={{ fontSize: '1.65rem', fontWeight: 800, margin: 0, color: '#fff', letterSpacing: '-0.02em' }}>
                BugFlow
              </h1>
            </div>

            <h2 style={{ fontSize: '1.75rem', fontWeight: 800, lineHeight: '1.3', color: '#fff', marginBottom: '0.75rem', letterSpacing: '-0.02em' }}>
              Defect tracking & sprint intelligence.
            </h2>
            <p style={{ color: '#cbd5e1', fontSize: '0.92rem', lineHeight: '1.6', marginBottom: '2rem' }}>
              Track bugs, manage sprints, and analyze blast radius impact with AI-assisted workflows.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.88rem', color: '#f8fafc' }}>
                <div style={{ width: '28px', height: '28px', borderRadius: '7px', background: 'rgba(255,255,255,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#818cf8', flexShrink: 0 }}>
                  <Zap size={15} />
                </div>
                <span>Real-time defect tracking & sprint board</span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.88rem', color: '#f8fafc' }}>
                <div style={{ width: '28px', height: '28px', borderRadius: '7px', background: 'rgba(255,255,255,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#38bdf8', flexShrink: 0 }}>
                  <Cpu size={15} />
                </div>
                <span>Autonomous blast radius impact analysis</span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.88rem', color: '#f8fafc' }}>
                <div style={{ width: '28px', height: '28px', borderRadius: '7px', background: 'rgba(255,255,255,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#a78bfa', flexShrink: 0 }}>
                  <Sparkles size={15} />
                </div>
                <span>AI-assisted duplicate detection & triage</span>
              </div>
            </div>
          </div>

          <div style={{ marginTop: '3rem', fontSize: '0.78rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Lock size={13} color="#94a3b8" />
            <span>Secure Role-Based Access Control</span>
          </div>
        </section>

        {/* Right Side: Authentication Form */}
        <div className="auth-card">
          <div style={{ marginBottom: '1.5rem' }}>
            <h2 style={{ fontSize: '1.45rem', fontWeight: 800, margin: '0 0 0.35rem 0', color: 'var(--text)', letterSpacing: '-0.02em' }}>
              {mode === 'login' ? 'Welcome back' : 'Create an account'}
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', margin: 0 }}>
              {mode === 'login' ? 'Enter your credentials to access your workspace.' : 'Fill in the details to create your workspace account.'}
            </p>
          </div>

          {/* Mode Tabs */}
          <div className="auth-tabs" style={{ marginBottom: '1.5rem' }}>
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
              Sign Up
            </button>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Email */}
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="email" style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text)', marginBottom: '0.35rem', display: 'block' }}>
                Email
              </label>
              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <Mail size={16} style={{ position: 'absolute', left: '0.85rem', color: 'var(--text-dim)', pointerEvents: 'none' }} />
                <input
                  id="email"
                  type="email"
                  value={email}
                  placeholder="name@company.com"
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  style={{
                    width: '100%',
                    padding: '0.65rem 0.85rem 0.65rem 2.4rem',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    background: 'var(--surface)',
                    color: 'var(--text)',
                    fontSize: '0.9rem',
                  }}
                />
              </div>
            </div>

            {/* Username & Role (Register Mode) */}
            {mode === 'register' && (
              <>
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label htmlFor="username" style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text)', marginBottom: '0.35rem', display: 'block' }}>
                    Username
                  </label>
                  <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                    <User size={16} style={{ position: 'absolute', left: '0.85rem', color: 'var(--text-dim)', pointerEvents: 'none' }} />
                    <input
                      id="username"
                      type="text"
                      value={username}
                      placeholder="alex_dev"
                      onChange={(e) => setUsername(e.target.value)}
                      required
                      minLength={3}
                      autoComplete="username"
                      style={{
                        width: '100%',
                        padding: '0.65rem 0.85rem 0.65rem 2.4rem',
                        borderRadius: '8px',
                        border: '1px solid var(--border)',
                        background: 'var(--surface)',
                        color: 'var(--text)',
                        fontSize: '0.9rem',
                      }}
                    />
                  </div>
                </div>

                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label htmlFor="role" style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text)', marginBottom: '0.35rem', display: 'block' }}>
                    Role
                  </label>
                  <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                    <Shield size={16} style={{ position: 'absolute', left: '0.85rem', color: 'var(--text-dim)', pointerEvents: 'none' }} />
                    <select
                      id="role"
                      value={role}
                      onChange={(e) => setRole(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '0.65rem 0.85rem 0.65rem 2.4rem',
                        borderRadius: '8px',
                        border: '1px solid var(--border)',
                        background: 'var(--surface)',
                        color: 'var(--text)',
                        fontSize: '0.9rem',
                        cursor: 'pointer',
                      }}
                    >
                      <option value="developer">Developer</option>
                      <option value="qa_tester">QA Tester</option>
                      <option value="project_manager">Project Manager</option>
                      <option value="admin">Admin</option>
                      <option value="reporter">Reporter</option>
                    </select>
                  </div>
                </div>
              </>
            )}

            {/* Password */}
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="password" style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text)', marginBottom: '0.35rem', display: 'block' }}>
                Password
              </label>
              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <Lock size={16} style={{ position: 'absolute', left: '0.85rem', color: 'var(--text-dim)', pointerEvents: 'none' }} />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  placeholder="••••••••••••"
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  style={{
                    width: '100%',
                    padding: '0.65rem 2.4rem 0.65rem 2.4rem',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    background: 'var(--surface)',
                    color: 'var(--text)',
                    fontSize: '0.9rem',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '0.75rem',
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-dim)',
                    cursor: 'pointer',
                    padding: '0.2rem',
                    display: 'flex',
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.6rem 0.8rem',
                borderRadius: '6px',
                background: 'var(--danger-light)',
                border: '1px solid var(--danger-border)',
                color: 'var(--danger-text)',
                fontSize: '0.82rem',
                fontWeight: 600,
              }}>
                <AlertCircle size={15} style={{ flexShrink: 0 }} />
                <span>{error}</span>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{
                width: '100%',
                padding: '0.75rem',
                fontSize: '0.92rem',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                borderRadius: '8px',
                marginTop: '0.25rem',
              }}
            >
              <span>{loading ? 'Signing in...' : mode === 'login' ? 'Sign In' : 'Create Account'}</span>
              <ArrowRight size={16} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
