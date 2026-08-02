import { useEffect, useState } from 'react';
import {
  Bot,
  LayoutDashboard,
  Bug,
  Target,
  Zap,
  FolderKanban,
  Sparkles,
  ShieldCheck,
  LogOut,
  Bell,
  Flame,
  Calendar,
  Users,
  History,
  Table,
  Kanban,
  Info,
  Eye,
  Trash2,
  User,
  Check,
  Plus,
} from 'lucide-react';
import {
  addProjectMember,
  createIssue,
  createProject,
  deleteIssue,
  deleteProject,
  getAllIssues,
  getDashboardStats,
  getProjectMembers,
  getProjects,
  getUsers,
  updateIssueStatus,
} from '../api';
import { useAuth } from '../AuthContext';
import AdminPanel from './AdminPanel';
import BugDetailModal from './BugDetailModal';
import CodeDoctor from './CodeDoctor';
import IssueForm from './IssueForm';
import NotificationDrawer from './NotificationDrawer';
import SprintManager from './SprintManager';
import ThemeToggle from './ThemeToggle';

function Badge({ value }) {
  const v = value || 'open';
  return (
    <span className={`badge badge-${v}`}>
      {v.replace('_', ' ')}
    </span>
  );
}

// ── SVG Charts Components ───────────────────────────────────────────────────

function SeverityChart({ data = {} }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  const items = [
    { label: 'Low', count: data.low || 0, color: '#3b82f6' },
    { label: 'Medium', count: data.medium || 0, color: '#eab308' },
    { label: 'High', count: data.high || 0, color: '#f97316' },
    { label: 'Critical', count: data.critical || 0, color: '#ef4444' },
  ];

  return (
    <div className="chart-card">
      <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <Flame size={16} color="#ef4444" /> Bugs by Severity
      </h4>
      <div className="severity-bar-container" style={{ margin: '1rem 0' }}>
        <div style={{ display: 'flex', height: '14px', borderRadius: '7px', overflow: 'hidden', background: 'rgba(255,255,255,0.05)' }}>
          {items.map((item, i) => {
            const pct = (item.count / total) * 100;
            if (pct === 0) return null;
            return <div key={i} style={{ width: `${pct}%`, background: item.color }} title={`${item.label}: ${item.count}`} />;
          })}
        </div>
      </div>
      <div className="chart-legend" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
        {items.map((item, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: item.color }} />
            <span>{item.label}:</span>
            <strong>{item.count}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusChart({ data = {} }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  const items = [
    { label: 'Open', count: data.open || 0, color: '#6366f1' },
    { label: 'In Progress', count: data.in_progress || 0, color: '#0ea5e9' },
    { label: 'In Review', count: data.in_review || 0, color: '#a855f7' },
    { label: 'Resolved', count: data.resolved || 0, color: '#10b981' },
    { label: 'Closed', count: data.closed || 0, color: '#64748b' },
  ];

  return (
    <div className="chart-card">
      <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <Zap size={16} color="#6366f1" /> Bugs by Status
      </h4>
      <div style={{ margin: '1rem 0' }}>
        <div style={{ display: 'flex', height: '14px', borderRadius: '7px', overflow: 'hidden', background: 'rgba(255,255,255,0.05)' }}>
          {items.map((item, i) => {
            const pct = (item.count / total) * 100;
            if (pct === 0) return null;
            return <div key={i} style={{ width: `${pct}%`, background: item.color }} title={`${item.label}: ${item.count}`} />;
          })}
        </div>
      </div>
      <div className="chart-legend" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
        {items.map((item, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.82rem' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: item.color }} />
            <span>{item.label}:</span>
            <strong>{item.count}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function MonthlyChart({ data = [] }) {
  const defaultMonths = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
  const chartData = data.length > 0 ? data : defaultMonths.map((m) => ({ month: m, count: 0 }));
  
  const counts = chartData.map((d) => d.count);
  const maxVal = Math.max(...counts, 4);
  const totalBugs = counts.reduce((a, b) => a + b, 0);

  const svgWidth = 400;
  const svgHeight = 160;
  const paddingLeft = 32;
  const paddingBottom = 25;
  const paddingTop = 25;
  const paddingRight = 15;

  const chartWidth = svgWidth - paddingLeft - paddingRight;
  const chartHeight = svgHeight - paddingTop - paddingBottom;
  const barWidth = Math.min(26, (chartWidth / chartData.length) * 0.55);

  return (
    <div className="chart-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', margin: 0 }}>
          <Calendar size={16} color="var(--accent)" /> Monthly Bug Reports
        </h4>
        <span style={{ fontSize: '0.75rem', fontWeight: '700', padding: '0.15rem 0.55rem', borderRadius: '12px', background: 'var(--accent-light)', color: 'var(--accent)', border: '1px solid var(--border)' }}>
          {totalBugs} total
        </span>
      </div>

      <div style={{ width: '100%', overflowX: 'auto' }}>
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          style={{ width: '100%', height: 'auto', display: 'block' }}
        >
          {/* Background Grid Lines & Y Labels */}
          {[0, 0.5, 1].map((ratio, i) => {
            const y = paddingTop + chartHeight * (1 - ratio);
            const val = Math.round(maxVal * ratio);
            return (
              <g key={i}>
                <text
                  x={paddingLeft - 8}
                  y={y + 3}
                  textAnchor="end"
                  fill="var(--text-dim)"
                  fontSize="10"
                  fontWeight="600"
                >
                  {val}
                </text>
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={svgWidth - paddingRight}
                  y2={y}
                  stroke="var(--border)"
                  strokeDasharray={ratio === 0 ? 'none' : '3 3'}
                  strokeWidth={ratio === 0 ? '1.5' : '1'}
                  opacity={ratio === 0 ? 0.8 : 0.4}
                />
              </g>
            );
          })}

          {/* Bars and Month Labels */}
          {chartData.map((item, i) => {
            const step = chartWidth / chartData.length;
            const x = paddingLeft + i * step + (step - barWidth) / 2;
            const height = maxVal > 0 ? (item.count / maxVal) * chartHeight : 0;
            const y = paddingTop + chartHeight - height;

            return (
              <g key={i} className="svg-bar-group" style={{ cursor: 'pointer' }}>
                {/* Value Label above Bar */}
                <text
                  x={x + barWidth / 2}
                  y={y - 5}
                  textAnchor="middle"
                  fill={item.count > 0 ? 'var(--accent)' : 'var(--text-dim)'}
                  fontSize="10"
                  fontWeight="700"
                >
                  {item.count}
                </text>

                {/* Bar Rect */}
                <rect
                  x={x}
                  y={Math.min(y, paddingTop + chartHeight - 3)}
                  width={barWidth}
                  height={Math.max(height, 3)}
                  rx="4"
                  ry="4"
                  fill={item.count > 0 ? 'url(#skyBlueGrad)' : 'var(--bg-dark-accent)'}
                  stroke={item.count > 0 ? '#38bdf8' : 'var(--border)'}
                  strokeWidth="1"
                />

                {/* X-Axis Month Label */}
                <text
                  x={x + barWidth / 2}
                  y={svgHeight - 6}
                  textAnchor="middle"
                  fill="var(--text-muted)"
                  fontSize="10"
                  fontWeight="600"
                >
                  {item.month}
                </text>
              </g>
            );
          })}

          {/* SVG Gradient Defs */}
          <defs>
            <linearGradient id="skyBlueGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" />
              <stop offset="100%" stopColor="#0284c7" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </div>
  );
}

function WorkloadChart({ data = [] }) {
  const maxCount = Math.max(...data.map((d) => d.count), 5);

  return (
    <div className="chart-card">
      <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
        <Users size={16} color="#0d9488" /> Developer Workload
      </h4>
      <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {data.length === 0 ? (
          <p className="text-muted">No assigned workload.</p>
        ) : (
          data.map((item, i) => {
            const widthPct = (item.count / maxCount) * 100;
            return (
              <div key={i}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.2rem' }}>
                  <span>{item.developer}</span>
                  <strong>{item.count} bugs</strong>
                </div>
                <div style={{ height: '8px', background: 'var(--bg-dark-accent)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${Math.max(widthPct, 4)}%`, height: '100%', background: '#0d9488', borderRadius: '4px' }} />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

// ── Main Dashboard Component ────────────────────────────────────────────────

export default function Dashboard() {
  const { user, logout, hasRole, isAdmin } = useAuth();
  const [navTab, setNavTab] = useState('dashboard'); // 'dashboard' | 'projects' | 'issues' | 'my_bugs' | 'sprints' | 'ai_tools' | 'admin'
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [issues, setIssues] = useState([]);
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [priorityFilter, setPriorityFilter] = useState('all');
  const [viewMode, setViewMode] = useState('list'); // 'list' | 'kanban'

  // Modals
  const [showNewProject, setShowNewProject] = useState(false);
  const [showNewIssue, setShowNewIssue] = useState(false);
  const [showMembersModal, setShowMembersModal] = useState(false);
  const [projectMembers, setProjectMembers] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [selectedAddUserId, setSelectedAddUserId] = useState('');
  const [notifOpen, setNotifOpen] = useState(false);

  // Form State
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    loadIssuesAndStats();
  }, [selectedProject, navTab, statusFilter, severityFilter, priorityFilter, searchQuery]);

  async function loadProjects() {
    try {
      const data = await getProjects();
      setProjects(data);
      if (data.length && !selectedProject) setSelectedProject(data[0]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadIssuesAndStats() {
    try {
      const pId = selectedProject ? selectedProject.id : null;
      const [statsData, issuesData] = await Promise.all([
        getDashboardStats(pId),
        getAllIssues({
          project_id: pId,
          search: searchQuery,
          status: statusFilter,
          severity: severityFilter,
          priority: priorityFilter,
          my_bugs_only: navTab === 'my_bugs',
        }),
      ]);
      setStats(statsData);
      setIssues(issuesData);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCreateProject(e) {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    try {
      const p = await createProject({ name: newProjectName, description: newProjectDesc });
      setProjects((prev) => [p, ...prev]);
      setSelectedProject(p);
      setNewProjectName('');
      setNewProjectDesc('');
      setShowNewProject(false);
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleDeleteProject(pId) {
    if (!window.confirm('Delete project and all its issues?')) return;
    try {
      await deleteProject(pId);
      const updated = projects.filter((p) => p.id !== pId);
      setProjects(updated);
      setSelectedProject(updated[0] || null);
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleOpenMembersModal(p) {
    setSelectedProject(p);
    setShowMembersModal(true);
    try {
      const [mList, uList] = await Promise.all([getProjectMembers(p.id), getUsers()]);
      setProjectMembers(mList);
      setAllUsers(uList);
    } catch {
      // ignore
    }
  }

  async function handleAddMember(e) {
    e.preventDefault();
    if (!selectedAddUserId) return;
    try {
      const m = await addProjectMember(selectedProject.id, { user_id: parseInt(selectedAddUserId) });
      setProjectMembers((prev) => [...prev, m]);
      setSelectedAddUserId('');
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleCreateIssueSubmit(payload) {
    if (!selectedProject) {
      alert('Please create or select a project first!');
      return;
    }
    await createIssue(selectedProject.id, payload);
    setShowNewIssue(false);
    loadIssuesAndStats();
  }

  async function handleQuickStatusUpdate(issueId, newStatus) {
    try {
      await updateIssueStatus(issueId, newStatus);
      loadIssuesAndStats();
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleDeleteIssue(issueId) {
    if (!window.confirm('Delete this bug?')) return;
    try {
      await deleteIssue(issueId);
      loadIssuesAndStats();
    } catch (err) {
      alert(err.message);
    }
  }

  const KANBAN_COLS = [
    { id: 'open', title: 'Open' },
    { id: 'in_progress', title: 'In Progress' },
    { id: 'in_review', title: 'In Review' },
    { id: 'resolved', title: 'Resolved' },
    { id: 'closed', title: 'Closed' },
  ];

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-icon">
            <Bot size={22} color="#ffffff" />
          </div>
          <div className="brand-text">
            <h2>BugFlow</h2>
          </div>
        </div>

        <div className="project-selector">
          <label>ACTIVE PROJECT</label>
          <select
            value={selectedProject?.id || ''}
            onChange={(e) => {
              const p = projects.find((x) => x.id === parseInt(e.target.value));
              setSelectedProject(p);
            }}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <nav className="nav-menu">
          <button className={`nav-item ${navTab === 'dashboard' ? 'active' : ''}`} onClick={() => setNavTab('dashboard')}>
            <LayoutDashboard size={16} /> Dashboard
          </button>
          <button className={`nav-item ${navTab === 'issues' ? 'active' : ''}`} onClick={() => setNavTab('issues')}>
            <Bug size={16} /> Bugs & Issues
          </button>
          <button className={`nav-item ${navTab === 'my_bugs' ? 'active' : ''}`} onClick={() => setNavTab('my_bugs')}>
            <Target size={16} /> My Bugs
          </button>
          <button className={`nav-item ${navTab === 'sprints' ? 'active' : ''}`} onClick={() => setNavTab('sprints')}>
            <Zap size={16} /> Sprint Board
          </button>
          <button className={`nav-item ${navTab === 'projects' ? 'active' : ''}`} onClick={() => setNavTab('projects')}>
            <FolderKanban size={16} /> Projects & Team
          </button>
          <button className={`nav-item ${navTab === 'ai_tools' ? 'active' : ''}`} onClick={() => setNavTab('ai_tools')}>
            <Sparkles size={16} /> Code Doctor & AI
          </button>

          {isAdmin && (
            <button className={`nav-item ${navTab === 'admin' ? 'active' : ''}`} onClick={() => setNavTab('admin')}>
              <ShieldCheck size={16} /> Admin Panel
            </button>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="avatar">{user?.username?.[0]?.toUpperCase()}</div>
            <div className="user-details">
              <span className="username">{user?.username}</span>
              <span className="user-role">{user?.role}</span>
            </div>
          </div>
          <button className="btn-logout" onClick={logout} title="Sign Out">
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Top Navigation Bar */}
        <header className="top-navbar">
          <div className="top-navbar-actions">
            {/* Agent Watermark Badge */}
            <div className="agent-watermark-badge">
              <Bot size={14} color="var(--accent)" />
              <span>AGENT SYNTHESIZED UI</span>
            </div>

            <button className="btn btn-primary btn-sm" onClick={() => setShowNewIssue(true)} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
              <Plus size={14} /> Report Bug
            </button>

            <button className="btn-icon" onClick={() => setNotifOpen(true)} title="Notifications">
              <Bell size={16} />
            </button>

            <ThemeToggle />
          </div>
        </header>

        <div className="view-container">
          {/* TAB 1: DASHBOARD */}
          {navTab === 'dashboard' && stats && (
            <div>
              <div className="stats-grid">
                <div className="stat-card">
                  <span className="stat-number">{stats.summary.total_bugs}</span>
                  <span className="stat-label">Total Bugs</span>
                </div>
                <div className="stat-card">
                  <span className="stat-number">{stats.summary.open_bugs}</span>
                  <span className="stat-label">Open Bugs</span>
                </div>
                <div className="stat-card">
                  <span className="stat-number">{stats.summary.in_progress_bugs}</span>
                  <span className="stat-label">In Progress</span>
                </div>
                <div className="stat-card">
                  <span className="stat-number">{stats.summary.resolved_bugs}</span>
                  <span className="stat-label">Resolved / Closed</span>
                </div>
                <div className="stat-card">
                  <span className="stat-number" style={{ color: '#ef4444' }}>
                    {stats.summary.critical_bugs}
                  </span>
                  <span className="stat-label">Critical Defects</span>
                </div>
                <div className="stat-card">
                  <span className="stat-number" style={{ color: '#38bdf8' }}>
                    {stats.summary.assigned_bugs}
                  </span>
                  <span className="stat-label">Assigned to Me</span>
                </div>
              </div>

              <div className="charts-grid">
                <SeverityChart data={stats.charts.by_severity} />
                <StatusChart data={stats.charts.by_status} />
                <MonthlyChart data={stats.charts.monthly_reports} />
                <WorkloadChart data={stats.charts.developer_workload} />
              </div>

              <div className="recent-activity-section card" style={{ marginTop: '1.5rem' }}>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <History size={18} /> Recent Activity Feed
                </h3>
                <div className="activity-timeline">
                  {stats.recent_activities.length === 0 ? (
                    <p className="text-muted">No activity recorded yet.</p>
                  ) : (
                    stats.recent_activities.map((act) => (
                      <div key={act.id} className="activity-item">
                        <div className="act-bullet" />
                        <div className="act-content">
                          <div className="act-title">
                            <strong>{act.user?.username}</strong> — {act.action}
                          </div>
                          {act.details && <div className="act-details">{act.details}</div>}
                          <div className="act-time">{new Date(act.created_at).toLocaleString()}</div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: BUGS & ISSUES LIST / KANBAN */}
          {(navTab === 'issues' || navTab === 'my_bugs') && (
            <div>
              <div className="toolbar">
                <div className="filter-group">
                  <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                    <option value="all">All Statuses</option>
                    <option value="open">Open</option>
                    <option value="in_progress">In Progress</option>
                    <option value="in_review">In Review</option>
                    <option value="resolved">Resolved</option>
                    <option value="closed">Closed</option>
                  </select>

                  <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
                    <option value="all">All Severities</option>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>

                  <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
                    <option value="all">All Priorities</option>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>

                <div className="view-mode-toggle">
                  <button
                    className={`btn-sm ${viewMode === 'list' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setViewMode('list')}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                  >
                    <Table size={14} /> Table View
                  </button>
                  <button
                    className={`btn-sm ${viewMode === 'kanban' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setViewMode('kanban')}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                  >
                    <Kanban size={14} /> Kanban Board
                  </button>
                </div>
              </div>

              {viewMode === 'list' ? (
                <div className="data-table-wrapper">
                  <div style={{ padding: '0.75rem 1rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.02)' }}>
                    <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)', fontWeight: '600' }}>
                      Showing {issues.length} defect{issues.length === 1 ? '' : 's'}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                      <Info size={13} /> Click any row to view full reproduction steps & comments
                    </span>
                  </div>

                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Bug Key</th>
                        <th>Title & Summary</th>
                        <th>Severity</th>
                        <th>Priority</th>
                        <th>Status</th>
                        <th>Assigned Dev</th>
                        <th>Reporter</th>
                        <th>Created Date</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {issues.length === 0 ? (
                        <tr>
                          <td colSpan={9} style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--text-muted)' }}>
                            No software defects match your search or filter criteria.
                          </td>
                        </tr>
                      ) : (
                        issues.map((issue) => (
                          <tr key={issue.id} onClick={() => setSelectedIssue(issue)} style={{ cursor: 'pointer' }}>
                            <td style={{ whiteSpace: 'nowrap' }}>
                              <span className="bug-id-tag">#BUG-{issue.id}</span>
                            </td>
                            <td>
                              <div className="table-issue-title">
                                <strong>{issue.title}</strong>
                                <span className="table-issue-snippet">{issue.description}</span>
                              </div>
                            </td>
                            <td>
                              <Badge value={issue.severity} />
                            </td>
                            <td>
                              <Badge value={issue.priority} />
                            </td>
                            <td onClick={(e) => e.stopPropagation()}>
                              <select
                                className="status-select-inline"
                                value={issue.status}
                                onChange={(e) => handleQuickStatusUpdate(issue.id, e.target.value)}
                              >
                                <option value="open">Open</option>
                                <option value="in_progress">In Progress</option>
                                <option value="in_review">In Review</option>
                                <option value="resolved">Resolved</option>
                                <option value="closed">Closed</option>
                              </select>
                            </td>
                            <td>
                              <div className="user-chip">
                                <div className="user-chip-avatar">
                                  {(issue.assigned_developer?.username || 'U')[0].toUpperCase()}
                                </div>
                                <span>{issue.assigned_developer?.username || 'Unassigned'}</span>
                              </div>
                            </td>
                            <td>
                              <div className="user-chip">
                                <div className="user-chip-avatar" style={{ background: 'linear-gradient(135deg, #a855f7, #ec4899)' }}>
                                  {(issue.reporter?.username || 'S')[0].toUpperCase()}
                                </div>
                                <span>{issue.reporter?.username || 'System'}</span>
                              </div>
                            </td>
                            <td style={{ whiteSpace: 'nowrap', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                              {new Date(issue.created_at).toLocaleDateString()}
                            </td>
                            <td onClick={(e) => e.stopPropagation()} style={{ whiteSpace: 'nowrap' }}>
                              <div style={{ display: 'flex', gap: '0.4rem' }}>
                                <button
                                  className="btn-link-sm"
                                  onClick={() => setSelectedIssue(issue)}
                                  title="View Details"
                                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}
                                >
                                  <Eye size={13} /> View
                                </button>
                                <button
                                  className="btn-link-sm danger"
                                  onClick={() => handleDeleteIssue(issue.id)}
                                  title="Delete Bug"
                                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}
                                >
                                  <Trash2 size={13} /> Delete
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              ) : (
                /* Kanban View */
                <div className="kanban-board">
                  {KANBAN_COLS.map((col) => {
                    const colIssues = issues.filter((i) => i.status === col.id);

                    return (
                      <div key={col.id} className="kanban-col">
                        <div className="kanban-header">
                          <h3>{col.title}</h3>
                          <span className="kanban-count">{colIssues.length}</span>
                        </div>

                        <div className="kanban-cards">
                          {colIssues.map((issue) => (
                            <div key={issue.id} className="kanban-card" onClick={() => setSelectedIssue(issue)}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                                <span className="bug-id-tag">#{issue.id}</span>
                                <Badge value={issue.severity} />
                              </div>
                              <h4>{issue.title}</h4>
                              <div className="kanban-footer">
                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                                  <User size={12} /> {issue.assigned_developer?.username || 'Unassigned'}
                                </span>
                                <div style={{ display: 'flex', gap: '0.3rem' }}>
                                  {col.id !== 'resolved' && (
                                    <button
                                      className="btn-icon-xs"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleQuickStatusUpdate(issue.id, 'resolved');
                                      }}
                                      title="Mark Resolved"
                                    >
                                      <Check size={12} />
                                    </button>
                                  )}
                                  <button
                                    className="btn-icon-xs danger"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      handleDeleteIssue(issue.id);
                                    }}
                                    title="Delete Bug"
                                  >
                                    <Trash2 size={12} />
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: SPRINTS */}
          {navTab === 'sprints' && (
            <SprintManager projectId={selectedProject?.id} onRefresh={loadIssuesAndStats} />
          )}

          {/* TAB 4: PROJECTS MANAGEMENT */}
          {navTab === 'projects' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <FolderKanban size={20} className="text-accent" /> Project Management
                </h2>
                <button className="btn btn-primary" onClick={() => setShowNewProject(true)} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Plus size={16} /> Create New Project
                </button>
              </div>

              <div className="projects-grid">
                {projects.map((p) => (
                  <div key={p.id} className="project-card">
                    <h3>{p.name}</h3>
                    <p>{p.description || 'No description provided.'}</p>
                    <div className="project-meta">
                      <span>Owner: {p.owner?.username || 'Admin'}</span>
                      <span>Members: {p.members?.length || 1}</span>
                    </div>

                    <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
                      <button className="btn btn-secondary btn-sm" onClick={() => handleOpenMembersModal(p)} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                        <Users size={14} /> Team Members
                      </button>
                      {isAdmin && (
                        <button className="btn btn-secondary btn-sm danger" onClick={() => handleDeleteProject(p.id)} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                          <Trash2 size={14} /> Delete
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 5: AI CODE DOCTOR */}
          {navTab === 'ai_tools' && <CodeDoctor />}

          {/* TAB 6: ADMIN PANEL */}
          {navTab === 'admin' && isAdmin && <AdminPanel />}
        </div>
      </main>

      {/* MODALS */}
      {showNewIssue && (
        <div className="modal-overlay" onClick={() => setShowNewIssue(false)}>
          <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
            <h2>Report New Software Defect</h2>
            <IssueForm
              projectId={selectedProject?.id}
              onSubmit={handleCreateIssueSubmit}
              onCancel={() => setShowNewIssue(false)}
              submitLabel="Submit Bug Report"
            />
          </div>
        </div>
      )}

      {showNewProject && (
        <div className="modal-overlay" onClick={() => setShowNewProject(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create New Project</h2>
            <form onSubmit={handleCreateProject}>
              <div className="form-group">
                <label>Project Name *</label>
                <input
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="e.g. Payments Gateway Microservice"
                  required
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  placeholder="Project goal and scope..."
                  rows={3}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowNewProject(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showMembersModal && selectedProject && (
        <div className="modal-overlay" onClick={() => setShowMembersModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Team Members: {selectedProject.name}</h2>

            <form onSubmit={handleAddMember} style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
              <select
                value={selectedAddUserId}
                onChange={(e) => setSelectedAddUserId(e.target.value)}
                style={{ flex: 1 }}
                required
              >
                <option value="">-- Select User to Add --</option>
                {allUsers.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.username} ({u.role})
                  </option>
                ))}
              </select>
              <button type="submit" className="btn btn-primary btn-sm">
                Add Member
              </button>
            </form>

            <ul style={{ listStyle: 'none', padding: 0 }}>
              {projectMembers.map((m) => (
                <li key={m.id} style={{ padding: '0.5rem 0', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                  <strong>{m.user?.username}</strong> — Role: {m.role_in_project} ({m.user?.email})
                </li>
              ))}
            </ul>

            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={() => setShowMembersModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedIssue && (
        <BugDetailModal
          issue={selectedIssue}
          onClose={() => setSelectedIssue(null)}
          onRefresh={loadIssuesAndStats}
        />
      )}

      <NotificationDrawer isOpen={notifOpen} onClose={() => setNotifOpen(false)} />
    </div>
  );
}
