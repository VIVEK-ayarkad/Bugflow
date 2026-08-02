import { useEffect, useState } from 'react';
import { ShieldCheck, Trash2, Users, FolderKanban, Bug } from 'lucide-react';
import { deleteAdminUser, getAdminReports, getAdminUsers, updateUserRole } from '../api';
import { useAuth } from '../AuthContext';

export default function AdminPanel() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [reports, setReports] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [uData, rData] = await Promise.all([getAdminUsers(), getAdminReports()]);
      setUsers(uData);
      setReports(rData);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleRoleChange(userId, newRole) {
    try {
      await updateUserRole(userId, newRole);
      setUsers((prev) => prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u)));
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleRemoveUser(userTarget) {
    if (userTarget.id === currentUser?.id) {
      alert('You cannot remove your own admin account.');
      return;
    }

    if (
      !window.confirm(
        `Are you sure you want to remove user '${userTarget.username}' (${userTarget.email}) and revoke all permissions?`
      )
    ) {
      return;
    }

    setDeletingId(userTarget.id);
    try {
      await deleteAdminUser(userTarget.id);
      setUsers((prev) => prev.filter((u) => u.id !== userTarget.id));
      if (reports?.system_metrics) {
        setReports((prev) => ({
          ...prev,
          system_metrics: {
            ...prev.system_metrics,
            total_users: Math.max(0, prev.system_metrics.total_users - 1),
          },
        }));
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setDeletingId(null);
    }
  }

  if (loading) return <div>Loading Admin Panel...</div>;

  return (
    <div className="admin-panel">
      <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <ShieldCheck size={22} className="text-accent" />
        Admin Management & RBAC Control
      </h2>

      {reports?.system_metrics && (
        <div className="stats-grid" style={{ marginBottom: '1.5rem' }}>
          <div className="stat-card">
            <span className="stat-number">{reports.system_metrics.total_users}</span>
            <span className="stat-label">Total Platform Users</span>
          </div>
          <div className="stat-card">
            <span className="stat-number">{reports.system_metrics.total_projects}</span>
            <span className="stat-label">Active Projects</span>
          </div>
          <div className="stat-card">
            <span className="stat-number">{reports.system_metrics.total_bugs}</span>
            <span className="stat-label">System Bugs Recorded</span>
          </div>
        </div>
      )}

      <h3>User Roles & Permissions Matrix</h3>
      <div className="data-table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Username</th>
              <th>Email</th>
              <th>Current Role</th>
              <th>Joined Date</th>
              <th>Modify Role</th>
              <th>Remove User</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>#{u.id}</td>
                <td>
                  <strong>{u.username}</strong>
                  {u.id === currentUser?.id && (
                    <span style={{ marginLeft: '0.4rem', fontSize: '0.7rem', color: 'var(--accent)' }}>(You)</span>
                  )}
                </td>
                <td>{u.email}</td>
                <td>
                  <span className={`badge badge-role-${u.role}`}>{u.role}</span>
                </td>
                <td>{new Date(u.created_at).toLocaleDateString()}</td>
                <td>
                  <select
                    value={u.role}
                    onChange={(e) => handleRoleChange(u.id, e.target.value)}
                    className="select-sm"
                  >
                    <option value="admin">Admin</option>
                    <option value="project_manager">Project Manager</option>
                    <option value="developer">Developer</option>
                    <option value="qa_tester">QA Tester</option>
                    <option value="reporter">Reporter</option>
                  </select>
                </td>
                <td>
                  <button
                    className="btn btn-secondary btn-sm danger"
                    onClick={() => handleRemoveUser(u)}
                    disabled={deletingId === u.id || u.id === currentUser?.id}
                    title="Remove user account and revoke access"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                  >
                    <Trash2 size={13} />
                    {deletingId === u.id ? 'Removing...' : 'Remove User'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
