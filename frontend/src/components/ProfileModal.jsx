import { useState } from 'react';
import { User, Mail, Lock, Shield, Check, AlertCircle, X, KeyRound, Calendar } from 'lucide-react';
import { updateUserProfile } from '../api';
import { useAuth } from '../AuthContext';

export default function ProfileModal({ onClose }) {
  const { user, setUser } = useAuth();

  const [username, setUsername] = useState(user?.username || '');
  const [email, setEmail] = useState(user?.email || '');
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!username.trim() || username.trim().length < 3) {
      setError('Username must be at least 3 characters long.');
      return;
    }

    if (!email.trim() || !email.includes('@')) {
      setError('Please enter a valid email address.');
      return;
    }

    const payload = {
      username: username.trim(),
      email: email.trim(),
    };

    if (showPasswordChange && newPassword) {
      if (!currentPassword) {
        setError('Please provide your current password to set a new password.');
        return;
      }
      if (newPassword.length < 6) {
        setError('New password must be at least 6 characters.');
        return;
      }
      if (newPassword !== confirmPassword) {
        setError('New passwords do not match.');
        return;
      }
      payload.current_password = currentPassword;
      payload.new_password = newPassword;
    }

    setLoading(true);
    try {
      const updatedUser = await updateUserProfile(payload);
      setUser(updatedUser);
      setSuccess('Profile updated successfully!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setShowPasswordChange(false);
      setTimeout(() => {
        setSuccess('');
      }, 3500);
    } catch (err) {
      setError(err.message || 'Failed to update profile.');
    } finally {
      setLoading(false);
    }
  }

  const roleLabels = {
    admin: 'Administrator',
    project_manager: 'Project Manager',
    developer: 'Developer',
    qa_tester: 'QA Tester',
    reporter: 'Reporter',
  };

  const getInitials = (name) => {
    if (!name) return 'U';
    return name.slice(0, 2).toUpperCase();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '540px' }}>
        {/* Modal Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border)' }}>
          <h2 style={{ margin: 0, display: 'inline-flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.25rem' }}>
            <User size={20} color="var(--accent)" /> User Profile & Account Settings
          </h2>
          <button className="btn-icon" onClick={onClose} title="Close">
            <X size={18} />
          </button>
        </div>

        {/* User Card Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            padding: '1rem',
            borderRadius: 'var(--radius-md)',
            background: 'linear-gradient(135deg, rgba(79, 70, 229, 0.08), rgba(2, 132, 199, 0.08))',
            border: '1px solid var(--border)',
            marginBottom: '1.25rem',
          }}
        >
          <div
            style={{
              width: '52px',
              height: '52px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #4f46e5, #0284c7)',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: '800',
              fontSize: '1.2rem',
              boxShadow: '0 4px 12px rgba(79, 70, 229, 0.25)',
              flexShrink: 0,
            }}
          >
            {getInitials(user?.username)}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{user?.username}</h3>
              <span className="badge" style={{ background: 'var(--accent-light)', color: 'var(--accent)', borderColor: 'var(--border)' }}>
                <Shield size={11} style={{ marginRight: '0.2rem' }} />
                {roleLabels[user?.role] || user?.role}
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
              <span>{user?.email}</span>
              {user?.created_at && (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                  <Calendar size={12} /> Joined {new Date(user.created_at).toLocaleDateString()}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Alerts */}
        {error && (
          <div className="alert alert-error" style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {success && (
          <div className="alert alert-success" style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Check size={16} /> {success}
          </div>
        )}

        {/* Profile Edit Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <User size={14} color="var(--text-dim)" /> Username *
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. alex_developer"
              required
              minLength={3}
              maxLength={100}
            />
          </div>

          <div className="form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Mail size={14} color="var(--text-dim)" /> Email Address *
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. alex@example.com"
              required
            />
          </div>

          {/* Password Change Toggle */}
          <div style={{ marginTop: '0.25rem' }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setShowPasswordChange(!showPasswordChange)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem' }}
            >
              <KeyRound size={13} />
              {showPasswordChange ? 'Cancel Password Change' : 'Change Password'}
            </button>
          </div>

          {showPasswordChange && (
            <div
              style={{
                padding: '1rem',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-dark-accent)',
                border: '1px solid var(--border)',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.85rem',
              }}
            >
              <h4 style={{ margin: 0, fontSize: '0.88rem', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Lock size={14} /> Update Security Password
              </h4>

              <div className="form-group" style={{ margin: 0 }}>
                <label style={{ fontSize: '0.8rem' }}>Current Password *</label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter current password"
                  required={showPasswordChange}
                />
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label style={{ fontSize: '0.8rem' }}>New Password (min 6 characters) *</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  required={showPasswordChange}
                  minLength={6}
                />
              </div>

              <div className="form-group" style={{ margin: 0 }}>
                <label style={{ fontSize: '0.8rem' }}>Confirm New Password *</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter new password"
                  required={showPasswordChange}
                  minLength={6}
                />
              </div>
            </div>
          )}

          {/* Form Actions */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.6rem', marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              {loading ? 'Saving...' : 'Save Profile Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
