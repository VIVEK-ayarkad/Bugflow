import { useEffect, useState } from 'react';
import {
  Zap,
  Play,
  CheckCircle2,
  Sparkles,
  Plus,
  Trash2,
  Calendar,
  Clock,
  BarChart3,
  Layers,
  ArrowRight,
  ArrowLeft,
  RefreshCw,
  Edit3,
  User,
  Search,
  CheckSquare,
  FileText,
  Activity,
  Flame,
  Check,
  TrendingDown,
  Info,
} from 'lucide-react';
import {
  aiSprintAdvisor,
  aiSprintHealth,
  aiSprintRetrospective,
  bulkAssignSprintIssues,
  completeSprint,
  createSprint,
  deleteSprint,
  getSprintMetrics,
  getSprints,
  startSprint,
  updateIssueStatus,
  updateSprint,
} from '../api';

export default function SprintManager({
  projectId,
  project,
  issues = [],
  onSelectIssue,
  onRefresh,
}) {
  const [sprints, setSprints] = useState([]);
  const [selectedSprintId, setSelectedSprintId] = useState(null);
  const [activeTab, setActiveTab] = useState('board'); // 'board' | 'planner' | 'analytics' | 'ai_copilot' | 'archive'
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  // Modals state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showCompleteModal, setShowCompleteModal] = useState(false);

  // Create/Edit Sprint Form State
  const [sprintForm, setSprintForm] = useState({
    name: '',
    goal: '',
    start_date: '',
    end_date: '',
  });

  // Complete Sprint Modal State
  const [completeOption, setCompleteOption] = useState('backlog'); // 'rollover' | 'backlog' | 'keep'
  const [rolloverTargetId, setRolloverTargetId] = useState('');

  // Backlog Planner State
  const [backlogSearch, setBacklogSearch] = useState('');
  const [selectedBacklogIds, setSelectedBacklogIds] = useState([]);
  const [selectedSprintIssueIds, setSelectedSprintIssueIds] = useState([]);
  const [assignLoading, setAssignLoading] = useState(false);

  // Burndown Analytics State
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [burndownMode, setBurndownMode] = useState('intraday'); // 'intraday' | 'milestones'

  // AI Analytics State
  const [aiHealth, setAiHealth] = useState(null);
  const [aiRetro, setAiRetro] = useState(null);
  const [aiAdvisor, setAiAdvisor] = useState(null);
  const [aiLoading, setAiLoading] = useState({ health: false, retro: false, advisor: false });

  useEffect(() => {
    if (projectId) {
      loadSprints();
    }
  }, [projectId]);

  useEffect(() => {
    if (selectedSprintId) {
      loadMetrics(selectedSprintId);
    } else {
      setMetrics(null);
    }
  }, [selectedSprintId]);

  async function loadSprints(preferredId = null) {
    setLoading(true);
    try {
      const data = await getSprints(projectId);
      setSprints(data);

      if (data.length > 0) {
        if (preferredId && data.some((s) => s.id === preferredId)) {
          setSelectedSprintId(preferredId);
        } else {
          // Default to active sprint, or the first one if no active sprint
          const active = data.find((s) => s.status === 'active');
          if (active) {
            setSelectedSprintId(active.id);
          } else if (!selectedSprintId || !data.some((s) => s.id === selectedSprintId)) {
            setSelectedSprintId(data[0].id);
          }
        }
      } else {
        setSelectedSprintId(null);
      }
    } catch (err) {
      console.error('Failed to load sprints:', err);
    } finally {
      setLoading(false);
    }
  }

  async function loadMetrics(sprintId) {
    try {
      const data = await getSprintMetrics(sprintId);
      setMetrics(data);
    } catch (err) {
      console.error('Failed to load sprint metrics:', err);
    }
  }

  const selectedSprint = sprints.find((s) => s.id === selectedSprintId);

  // Helper date preset calculation
  function applyDurationPreset(weeks) {
    const start = new Date();
    const end = new Date();
    end.setDate(start.getDate() + weeks * 7);

    setSprintForm((prev) => ({
      ...prev,
      start_date: start.toISOString().split('T')[0],
      end_date: end.toISOString().split('T')[0],
    }));
  }

  function handleOpenCreateModal() {
    const nextNum = sprints.length + 1;
    const start = new Date();
    const end = new Date();
    end.setDate(start.getDate() + 14);

    setSprintForm({
      name: `Sprint ${nextNum} - ${project?.name || 'Iteration'}`,
      goal: '',
      start_date: start.toISOString().split('T')[0],
      end_date: end.toISOString().split('T')[0],
    });
    setShowCreateModal(true);
  }

  function handleOpenEditModal(sprint) {
    setSprintForm({
      name: sprint.name,
      goal: sprint.goal || '',
      start_date: sprint.start_date ? sprint.start_date.split('T')[0] : '',
      end_date: sprint.end_date ? sprint.end_date.split('T')[0] : '',
    });
    setShowEditModal(true);
  }

  async function handleCreateSprint(e) {
    e.preventDefault();
    if (!sprintForm.name.trim()) return;

    try {
      const payload = {
        name: sprintForm.name.trim(),
        goal: sprintForm.goal?.trim() || null,
        start_date: sprintForm.start_date ? new Date(sprintForm.start_date).toISOString() : null,
        end_date: sprintForm.end_date ? new Date(sprintForm.end_date).toISOString() : null,
      };
      const created = await createSprint(projectId, payload);
      setShowCreateModal(false);
      await loadSprints(created.id);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(err.message || 'Failed to create sprint');
    }
  }

  async function handleUpdateSprint(e) {
    e.preventDefault();
    if (!selectedSprintId || !sprintForm.name.trim()) return;

    try {
      const payload = {
        name: sprintForm.name.trim(),
        goal: sprintForm.goal?.trim() || null,
        start_date: sprintForm.start_date ? new Date(sprintForm.start_date).toISOString() : null,
        end_date: sprintForm.end_date ? new Date(sprintForm.end_date).toISOString() : null,
      };
      await updateSprint(selectedSprintId, payload);
      setShowEditModal(false);
      await loadSprints(selectedSprintId);
      loadMetrics(selectedSprintId);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(err.message || 'Failed to update sprint');
    }
  }

  async function handleStartSprint(sprintId) {
    try {
      await startSprint(sprintId);
      await loadSprints(sprintId);
      loadMetrics(sprintId);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(err.message || 'Failed to start sprint');
    }
  }

  function handleOpenCompleteModal() {
    const plannedSprints = sprints.filter((s) => s.id !== selectedSprintId && s.status === 'planning');
    setRolloverTargetId(plannedSprints[0]?.id || '');
    setCompleteOption(plannedSprints.length > 0 ? 'rollover' : 'backlog');
    setShowCompleteModal(true);
  }

  async function handleConfirmCompleteSprint() {
    if (!selectedSprintId) return;

    try {
      const payload = {
        action: completeOption,
        rollover_sprint_id: completeOption === 'rollover' ? parseInt(rolloverTargetId) || null : null,
      };
      await completeSprint(selectedSprintId, payload);
      setShowCompleteModal(false);
      await loadSprints();
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(err.message || 'Failed to complete sprint');
    }
  }

  async function handleDeleteSprint(sprintId, sprintName) {
    if (!window.confirm(`Are you sure you want to delete '${sprintName}'? All assigned defects will be moved back to the backlog.`)) {
      return;
    }
    try {
      await deleteSprint(sprintId);
      await loadSprints();
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(err.message || 'Failed to delete sprint');
    }
  }

  async function handleQuickStatusChange(issueId, newStatus) {
    try {
      await updateIssueStatus(issueId, newStatus);
      if (selectedSprintId) loadMetrics(selectedSprintId);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(err.message || 'Failed to update issue status');
    }
  }

  // Backlog Planner Actions
  async function handleBulkAssignToSprint(issueIds) {
    if (!selectedSprintId || !issueIds.length) return;
    setAssignLoading(true);
    try {
      await bulkAssignSprintIssues(selectedSprintId, {
        issue_ids: issueIds,
        action: 'add',
      });
      setSelectedBacklogIds([]);
      loadMetrics(selectedSprintId);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(err.message || 'Failed to assign issues to sprint');
    } finally {
      setAssignLoading(false);
    }
  }

  async function handleBulkRemoveFromSprint(issueIds) {
    if (!selectedSprintId || !issueIds.length) return;
    setAssignLoading(true);
    try {
      await bulkAssignSprintIssues(selectedSprintId, {
        issue_ids: issueIds,
        action: 'remove',
      });
      setSelectedSprintIssueIds([]);
      loadMetrics(selectedSprintId);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(err.message || 'Failed to remove issues from sprint');
    } finally {
      setAssignLoading(false);
    }
  }

  // AI Copilot Actions
  async function handleRunAiHealth() {
    if (!selectedSprintId) return;
    setAiLoading((prev) => ({ ...prev, health: true }));
    try {
      const res = await aiSprintHealth(selectedSprintId);
      setAiHealth(res);
    } catch (err) {
      alert(err.message || 'AI Health analysis failed');
    } finally {
      setAiLoading((prev) => ({ ...prev, health: false }));
    }
  }

  async function handleRunAiRetro() {
    if (!selectedSprintId) return;
    setAiLoading((prev) => ({ ...prev, retro: true }));
    try {
      const res = await aiSprintRetrospective(selectedSprintId);
      setAiRetro(res);
    } catch (err) {
      alert(err.message || 'AI Retrospective generation failed');
    } finally {
      setAiLoading((prev) => ({ ...prev, retro: false }));
    }
  }

  async function handleRunAiAdvisor() {
    if (!selectedSprintId) return;
    setAiLoading((prev) => ({ ...prev, advisor: true }));
    try {
      const res = await aiSprintAdvisor(selectedSprintId);
      setAiAdvisor(res);
    } catch (err) {
      alert(err.message || 'AI Advisor analysis failed');
    } finally {
      setAiLoading((prev) => ({ ...prev, advisor: false }));
    }
  }

  // Derived issue sets
  const sprintIssues = issues.filter((i) => i.sprint_id === selectedSprintId);
  const backlogIssues = issues.filter(
    (i) =>
      (!i.sprint_id || i.sprint_id !== selectedSprintId) &&
      (backlogSearch === '' ||
        i.title.toLowerCase().includes(backlogSearch.toLowerCase()) ||
        String(i.id).includes(backlogSearch) ||
        (i.category && i.category.toLowerCase().includes(backlogSearch.toLowerCase())))
  );

  const completedSprints = sprints.filter((s) => s.status === 'completed');
  const activeSprints = sprints.filter((s) => s.status === 'active');
  const planningSprints = sprints.filter((s) => s.status === 'planning');

  const boardColumns = [
    { id: 'open', label: 'Open', color: 'var(--text-muted)' },
    { id: 'in_progress', label: 'In Progress', color: 'var(--primary)' },
    { id: 'in_review', label: 'In Review', color: 'var(--accent)' },
    { id: 'resolved', label: 'Resolved / Done', color: 'var(--success)' },
  ];

  return (
    <div className="sprint-manager-view" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* ── Top Header Bar ────────────────────────────────────────────── */}
      <div
        className="sprint-top-bar"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          background: 'var(--surface)',
          padding: '1.25rem 1.5rem',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--border)',
          boxShadow: 'var(--shadow-soft)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
            }}
          >
            <Zap size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <h2 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 800 }}>Agile Sprint Operations</h2>
              <span className="badge" style={{ background: 'var(--accent-light)', color: 'var(--accent)', fontSize: '0.75rem' }}>
                {project?.name || 'Active Project'}
              </span>
            </div>
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {activeSprints.length} Active • {planningSprints.length} In Planning • {completedSprints.length} Completed
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => {
              loadSprints(selectedSprintId);
              if (selectedSprintId) loadMetrics(selectedSprintId);
            }}
            title="Refresh Sprint Telemetry"
          >
            <RefreshCw size={14} /> Refresh
          </button>

          <button
            className="btn btn-primary"
            onClick={handleOpenCreateModal}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}
          >
            <Plus size={16} /> New Sprint
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          <RefreshCw size={24} className="spin" style={{ margin: '0 auto 0.75rem' }} />
          Loading Agile Sprints...
        </div>
      ) : sprints.length === 0 ? (
        <div
          className="empty-state"
          style={{
            background: 'var(--surface)',
            border: '1px dashed var(--border)',
            borderRadius: 'var(--radius)',
            padding: '3.5rem 2rem',
            textAlign: 'center',
          }}
        >
          <Zap size={44} style={{ color: 'var(--accent)', opacity: 0.8, marginBottom: '1rem' }} />
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: '0 0 0.5rem' }}>No Sprints Created Yet</h3>
          <p style={{ color: 'var(--text-muted)', maxWidth: '460px', margin: '0 auto 1.5rem', fontSize: '0.9rem' }}>
            Plan milestone iterations, track real-time burndown progression, and organize bug resolution with automated sprint workflows.
          </p>
          <button className="btn btn-primary" onClick={handleOpenCreateModal} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
            <Plus size={16} /> Create Your First Sprint
          </button>
        </div>
      ) : (
        <>
          {/* ── Sprint Switcher & Action Control Ribbon ──────────────── */}
          <div
            style={{
              background: 'var(--surface)',
              borderRadius: 'var(--radius)',
              border: '1px solid var(--border)',
              padding: '1rem 1.25rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
              boxShadow: 'var(--shadow-soft)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                <label style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Target Sprint:
                </label>
                <select
                  value={selectedSprintId || ''}
                  onChange={(e) => setSelectedSprintId(parseInt(e.target.value))}
                  style={{
                    padding: '0.45rem 0.85rem',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-dark-accent)',
                    color: 'var(--text)',
                    fontWeight: 600,
                    fontSize: '0.9rem',
                    minWidth: '240px',
                  }}
                >
                  {sprints.map((s) => (
                    <option key={s.id} value={s.id}>
                      [{s.status.toUpperCase()}] {s.name}
                    </option>
                  ))}
                </select>

                {selectedSprint && (
                  <span
                    className={`badge badge-${selectedSprint.status}`}
                    style={{
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      padding: '0.25rem 0.65rem',
                    }}
                  >
                    {selectedSprint.status}
                  </span>
                )}
              </div>

              {selectedSprint && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {selectedSprint.status === 'planning' && (
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => handleStartSprint(selectedSprint.id)}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontWeight: 600 }}
                    >
                      <Play size={14} /> Start Sprint
                    </button>
                  )}

                  {selectedSprint.status === 'active' && (
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={handleOpenCompleteModal}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.35rem',
                        fontWeight: 600,
                        borderColor: 'var(--success)',
                        color: 'var(--success)',
                      }}
                    >
                      <CheckCircle2 size={14} /> Complete Sprint
                    </button>
                  )}

                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleOpenEditModal(selectedSprint)}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                    title="Edit Sprint Settings"
                  >
                    <Edit3 size={14} /> Edit
                  </button>

                  <button
                    className="btn btn-secondary btn-sm danger"
                    onClick={() => handleDeleteSprint(selectedSprint.id, selectedSprint.name)}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                    title="Delete Sprint"
                  >
                    <Trash2 size={14} /> Delete
                  </button>
                </div>
              )}
            </div>

            {/* Sprint Goal & Dates Banner */}
            {selectedSprint && (
              <div
                style={{
                  background: 'var(--bg-dark-accent)',
                  padding: '0.75rem 1rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '0.75rem',
                  fontSize: '0.85rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, minWidth: '220px' }}>
                  <span style={{ fontWeight: 700, color: 'var(--accent)' }}>GOAL:</span>
                  <span style={{ color: selectedSprint.goal ? 'var(--text)' : 'var(--text-muted)', fontStyle: selectedSprint.goal ? 'normal' : 'italic' }}>
                    {selectedSprint.goal || 'No specific objective recorded for this sprint milestone.'}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  {selectedSprint.start_date && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                      <Calendar size={13} /> {new Date(selectedSprint.start_date).toLocaleDateString()}
                    </span>
                  )}
                  {selectedSprint.end_date && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                      <Clock size={13} /> End: {new Date(selectedSprint.end_date).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* KPI Progress Strip */}
            {metrics && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem', marginTop: '0.25rem' }}>
                <div style={{ background: 'var(--surface)', padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Completion</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent)', marginTop: '0.1rem' }}>
                    {Math.round(metrics.completion_rate * 100)}%
                  </div>
                  <div style={{ height: '4px', background: 'var(--border)', borderRadius: '2px', marginTop: '0.35rem', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${Math.round(metrics.completion_rate * 100)}%`, background: 'var(--accent)' }} />
                  </div>
                </div>

                <div style={{ background: 'var(--surface)', padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Total Issues</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text)', marginTop: '0.1rem' }}>
                    {metrics.total_issues}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    {metrics.resolved_issues + metrics.closed_issues} resolved
                  </div>
                </div>

                <div style={{ background: 'var(--surface)', padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>In Progress</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--primary)', marginTop: '0.1rem' }}>
                    {metrics.in_progress_issues}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    {metrics.in_review_issues} in review
                  </div>
                </div>

                <div style={{ background: 'var(--surface)', padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Open Defects</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--warning)', marginTop: '0.1rem' }}>
                    {metrics.open_issues}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Awaiting triage</div>
                </div>

                <div style={{ background: 'var(--surface)', padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Blockers</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: metrics.critical_issues > 0 ? 'var(--danger)' : 'var(--text-muted)', marginTop: '0.1rem' }}>
                    {metrics.critical_issues}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>Critical/High priority</div>
                </div>

                <div style={{ background: 'var(--surface)', padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Days Remaining</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text)', marginTop: '0.1rem' }}>
                    {metrics.days_remaining !== null ? `${metrics.days_remaining}d` : 'N/A'}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    {metrics.days_total ? `of ${metrics.days_total}d total` : 'Flexible target'}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* ── Sub-Navigation Tabs ──────────────────────────────────── */}
          <div
            style={{
              display: 'flex',
              gap: '0.5rem',
              borderBottom: '1px solid var(--border)',
              paddingBottom: '0.5rem',
              overflowX: 'auto',
            }}
          >
            <button
              className={`btn btn-sm ${activeTab === 'board' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('board')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}
            >
              <Layers size={15} /> Sprint Board ({sprintIssues.length})
            </button>

            <button
              className={`btn btn-sm ${activeTab === 'planner' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('planner')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}
            >
              <CheckSquare size={15} /> Scope & Backlog Planner
            </button>

            <button
              className={`btn btn-sm ${activeTab === 'analytics' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('analytics')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}
            >
              <BarChart3 size={15} /> Real-Time Burndown & Velocity
            </button>

            <button
              className={`btn btn-sm ${activeTab === 'ai_copilot' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('ai_copilot')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}
            >
              <Sparkles size={15} /> AI Sprint Copilot
            </button>

            <button
              className={`btn btn-sm ${activeTab === 'archive' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('archive')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600 }}
            >
              <FileText size={15} /> Milestones Archive ({completedSprints.length})
            </button>
          </div>

          {/* ── SUB-TAB 1: SPRINT KANBAN BOARD ──────────────────────── */}
          {activeTab === 'board' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {sprintIssues.length === 0 ? (
                <div
                  style={{
                    background: 'var(--surface)',
                    border: '1px dashed var(--border)',
                    borderRadius: 'var(--radius)',
                    padding: '3rem',
                    textAlign: 'center',
                  }}
                >
                  <Layers size={36} style={{ color: 'var(--text-muted)', marginBottom: '0.75rem' }} />
                  <h4 style={{ margin: '0 0 0.5rem', fontWeight: 700 }}>No Defects In This Sprint</h4>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
                    This sprint has no assigned defects yet. Use the Scope Planner to pull bugs from your project backlog.
                  </p>
                  <button className="btn btn-primary btn-sm" onClick={() => setActiveTab('planner')}>
                    Open Scope & Backlog Planner
                  </button>
                </div>
              ) : (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                    gap: '1rem',
                    alignItems: 'start',
                  }}
                >
                  {boardColumns.map((col) => {
                    const colIssues = sprintIssues.filter((i) => {
                      if (col.id === 'resolved') {
                        return i.status === 'resolved' || i.status === 'closed';
                      }
                      return i.status === col.id;
                    });

                    return (
                      <div
                        key={col.id}
                        style={{
                          background: 'var(--surface)',
                          borderRadius: 'var(--radius)',
                          border: '1px solid var(--border)',
                          display: 'flex',
                          flexDirection: 'column',
                          minHeight: '420px',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            padding: '0.75rem 1rem',
                            borderBottom: '1px solid var(--border)',
                            background: 'var(--bg-dark-accent)',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontWeight: 700, fontSize: '0.85rem' }}>
                            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: col.color }} />
                            <span>{col.label}</span>
                          </div>
                          <span className="badge" style={{ fontSize: '0.75rem', fontWeight: 700, background: 'var(--surface)', border: '1px solid var(--border)' }}>
                            {colIssues.length}
                          </span>
                        </div>

                        <div style={{ padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.65rem', flex: 1, overflowY: 'auto' }}>
                          {colIssues.length === 0 ? (
                            <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
                              No defects
                            </div>
                          ) : (
                            colIssues.map((issue) => (
                              <div
                                key={issue.id}
                                onClick={() => onSelectIssue && onSelectIssue(issue)}
                                style={{
                                  background: 'var(--bg-dark-accent)',
                                  border: '1px solid var(--border)',
                                  borderRadius: '8px',
                                  padding: '0.85rem',
                                  cursor: 'pointer',
                                  transition: 'all 0.15s ease',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '0.5rem',
                                }}
                                className="sprint-issue-card"
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', fontWeight: 700, color: 'var(--accent)' }}>
                                    #DEF-{issue.id}
                                  </span>
                                  <span
                                    className={`badge badge-${issue.severity}`}
                                    style={{ fontSize: '0.65rem', padding: '0.1rem 0.4rem', textTransform: 'capitalize' }}
                                  >
                                    {issue.severity}
                                  </span>
                                </div>

                                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text)', lineHeight: 1.3 }}>
                                  {issue.title}
                                </div>

                                {issue.category && (
                                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                    📁 {issue.category} {issue.module ? `• ${issue.module}` : ''}
                                  </div>
                                )}

                                <div
                                  style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    paddingTop: '0.4rem',
                                    borderTop: '1px solid var(--border)',
                                    fontSize: '0.75rem',
                                    color: 'var(--text-muted)',
                                  }}
                                >
                                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                                    <User size={12} /> {issue.assigned_developer?.username || 'Unassigned'}
                                  </span>

                                  <select
                                    value={issue.status}
                                    onClick={(e) => e.stopPropagation()}
                                    onChange={(e) => {
                                      e.stopPropagation();
                                      handleQuickStatusChange(issue.id, e.target.value);
                                    }}
                                    style={{
                                      fontSize: '0.7rem',
                                      padding: '0.15rem 0.4rem',
                                      borderRadius: '4px',
                                      background: 'var(--surface)',
                                      color: 'var(--text)',
                                      border: '1px solid var(--border)',
                                    }}
                                  >
                                    <option value="open">Open</option>
                                    <option value="in_progress">In Progress</option>
                                    <option value="in_review">In Review</option>
                                    <option value="resolved">Resolved</option>
                                    <option value="closed">Closed</option>
                                  </select>
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* ── SUB-TAB 2: DUAL-PANE SCOPE & BACKLOG PLANNER ────────── */}
          {activeTab === 'planner' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div
                style={{
                  background: 'var(--surface)',
                  padding: '1rem 1.25rem',
                  borderRadius: 'var(--radius)',
                  border: '1px solid var(--border)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '0.75rem',
                }}
              >
                <div>
                  <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Scope Triage & Multi-Select Assignment</h3>
                  <p style={{ margin: '0.2rem 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Move defects into {selectedSprint?.name} or back to the project backlog.
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  {selectedBacklogIds.length > 0 && (
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => handleBulkAssignToSprint(selectedBacklogIds)}
                      disabled={assignLoading}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                    >
                      <ArrowLeft size={14} /> Add {selectedBacklogIds.length} to Sprint
                    </button>
                  )}

                  {selectedSprintIssueIds.length > 0 && (
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleBulkRemoveFromSprint(selectedSprintIssueIds)}
                      disabled={assignLoading}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                    >
                      Remove {selectedSprintIssueIds.length} <ArrowRight size={14} />
                    </button>
                  )}
                </div>
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                  gap: '1.25rem',
                  alignItems: 'start',
                }}
              >
                {/* Left Pane: Current Sprint Scope */}
                <div
                  style={{
                    background: 'var(--surface)',
                    borderRadius: 'var(--radius)',
                    border: '1px solid var(--border)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      padding: '0.85rem 1rem',
                      background: 'var(--bg-dark-accent)',
                      borderBottom: '1px solid var(--border)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>Sprint Scope</span>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                        ({sprintIssues.length} defects committed)
                      </span>
                    </div>

                    {sprintIssues.length > 0 && (
                      <button
                        className="btn btn-link btn-sm"
                        style={{ fontSize: '0.75rem', padding: 0 }}
                        onClick={() => {
                          if (selectedSprintIssueIds.length === sprintIssues.length) {
                            setSelectedSprintIssueIds([]);
                          } else {
                            setSelectedSprintIssueIds(sprintIssues.map((i) => i.id));
                          }
                        }}
                      >
                        {selectedSprintIssueIds.length === sprintIssues.length ? 'Deselect All' : 'Select All'}
                      </button>
                    )}
                  </div>

                  <div style={{ padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '520px', overflowY: 'auto' }}>
                    {sprintIssues.length === 0 ? (
                      <div style={{ padding: '3rem 1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        No defects in sprint. Check items from the backlog on the right to commit them.
                      </div>
                    ) : (
                      sprintIssues.map((issue) => {
                        const isSelected = selectedSprintIssueIds.includes(issue.id);

                        return (
                          <div
                            key={issue.id}
                            style={{
                              background: isSelected ? 'var(--accent-light)' : 'var(--bg-dark-accent)',
                              border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                              borderRadius: '8px',
                              padding: '0.65rem 0.85rem',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              gap: '0.5rem',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flex: 1, minWidth: 0 }}>
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedSprintIssueIds((prev) => [...prev, issue.id]);
                                  } else {
                                    setSelectedSprintIssueIds((prev) => prev.filter((id) => id !== issue.id));
                                  }
                                }}
                              />
                              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent)', marginRight: '0.4rem' }}>
                                  #DEF-{issue.id}
                                </span>
                                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text)' }}>
                                  {issue.title}
                                </span>
                              </div>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                              <span className={`badge badge-${issue.severity}`} style={{ fontSize: '0.65rem' }}>
                                {issue.severity}
                              </span>
                              <button
                                className="btn btn-secondary btn-sm"
                                style={{ padding: '0.2rem 0.45rem', fontSize: '0.7rem' }}
                                onClick={() => handleBulkRemoveFromSprint([issue.id])}
                                title="Remove to backlog"
                              >
                                Remove
                              </button>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* Right Pane: Project Backlog */}
                <div
                  style={{
                    background: 'var(--surface)',
                    borderRadius: 'var(--radius)',
                    border: '1px solid var(--border)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      padding: '0.85rem 1rem',
                      background: 'var(--bg-dark-accent)',
                      borderBottom: '1px solid var(--border)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: '0.5rem',
                    }}
                  >
                    <div>
                      <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>Project Backlog</span>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                        ({backlogIssues.length} uncommitted)
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {backlogIssues.length > 0 && (
                        <button
                          className="btn btn-link btn-sm"
                          style={{ fontSize: '0.75rem', padding: 0 }}
                          onClick={() => {
                            if (selectedBacklogIds.length === backlogIssues.length) {
                              setSelectedBacklogIds([]);
                            } else {
                              setSelectedBacklogIds(backlogIssues.map((i) => i.id));
                            }
                          }}
                        >
                          {selectedBacklogIds.length === backlogIssues.length ? 'Deselect All' : 'Select All'}
                        </button>
                      )}
                    </div>
                  </div>

                  <div style={{ padding: '0.65rem 0.85rem', borderBottom: '1px solid var(--border)' }}>
                    <div style={{ position: 'relative' }}>
                      <Search size={14} style={{ position: 'absolute', left: '0.65rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                      <input
                        type="text"
                        placeholder="Filter backlog defects by title or category..."
                        value={backlogSearch}
                        onChange={(e) => setBacklogSearch(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '0.4rem 0.65rem 0.4rem 2rem',
                          borderRadius: '6px',
                          border: '1px solid var(--border)',
                          background: 'var(--bg-dark-accent)',
                          color: 'var(--text)',
                          fontSize: '0.8rem',
                        }}
                      />
                    </div>
                  </div>

                  <div style={{ padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '460px', overflowY: 'auto' }}>
                    {backlogIssues.length === 0 ? (
                      <div style={{ padding: '3rem 1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        No uncommitted defects found.
                      </div>
                    ) : (
                      backlogIssues.map((issue) => {
                        const isSelected = selectedBacklogIds.includes(issue.id);

                        return (
                          <div
                            key={issue.id}
                            style={{
                              background: isSelected ? 'var(--accent-light)' : 'var(--bg-dark-accent)',
                              border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                              borderRadius: '8px',
                              padding: '0.65rem 0.85rem',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              gap: '0.5rem',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flex: 1, minWidth: 0 }}>
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedBacklogIds((prev) => [...prev, issue.id]);
                                  } else {
                                    setSelectedBacklogIds((prev) => prev.filter((id) => id !== issue.id));
                                  }
                                }}
                              />
                              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', marginRight: '0.4rem' }}>
                                  #DEF-{issue.id}
                                </span>
                                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text)' }}>
                                  {issue.title}
                                </span>
                              </div>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                              <span className={`badge badge-${issue.severity}`} style={{ fontSize: '0.65rem' }}>
                                {issue.severity}
                              </span>
                              <button
                                className="btn btn-primary btn-sm"
                                style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem' }}
                                onClick={() => handleBulkAssignToSprint([issue.id])}
                                title="Add to sprint"
                              >
                                + Add
                              </button>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── SUB-TAB 3: HIGH-PRECISION REAL-TIME BURNDOWN & VELOCITY ── */}
          {activeTab === 'analytics' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {metrics && (
                <div
                  style={{
                    background: 'var(--surface)',
                    borderRadius: 'var(--radius)',
                    border: '1px solid var(--border)',
                    padding: '1.5rem',
                    boxShadow: 'var(--shadow-soft)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
                    <div>
                      <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Flame size={20} className="text-accent" /> High-Precision Sprint Burndown Progression
                      </h3>
                      <p style={{ margin: '0.3rem 0 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        Tracking ideal vs actual defect resolution throughout the sprint milestone in real time.
                      </p>
                    </div>

                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '1rem',
                        fontSize: '0.8rem',
                        background: 'var(--bg-dark-accent)',
                        padding: '0.45rem 0.85rem',
                        borderRadius: '20px',
                        border: '1px solid var(--border)',
                        flexWrap: 'wrap',
                      }}
                    >
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)' }}>
                        <div style={{ width: '14px', height: '2px', background: '#94a3b8', borderStyle: 'dashed' }} /> Ideal Guideline
                      </span>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent)', fontWeight: 600 }}>
                        <div style={{ width: '14px', height: '3px', background: 'var(--accent)', borderRadius: '2px' }} /> Actual Remaining
                      </span>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', color: 'var(--accent)', fontWeight: 700 }}>
                        <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#38bdf8', boxShadow: '0 0 8px #38bdf8' }} /> LIVE
                      </span>
                    </div>
                  </div>

                  {/* SVG High-Precision Burndown Chart */}
                  {metrics.burndown && metrics.burndown.length > 0 ? (
                    <div style={{ position: 'relative', width: '100%', height: '310px', paddingBottom: '10px' }}>
                      <svg
                        width="100%"
                        height="100%"
                        viewBox="0 0 760 290"
                        style={{ overflow: 'visible' }}
                        onMouseLeave={() => setHoveredPoint(null)}
                      >
                        <defs>
                          <linearGradient id="burndownGradPrecise" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#0284c7" stopOpacity="0.25" />
                            <stop offset="100%" stopColor="#0284c7" stopOpacity="0.0" />
                          </linearGradient>
                        </defs>

                        {/* Top Y-Axis Label */}
                        <text x="55" y="18" fill="var(--text-muted)" fontSize="9.5" fontWeight="700" letterSpacing="0.8px">
                          DEFECTS
                        </text>

                        {/* Chart Render Calculations */}
                        {(() => {
                          const points = metrics.burndown;
                          const maxVal = Math.max(1, metrics.total_issues || 1);
                          const numDays = Math.max(1, metrics.days_total || 14);

                          const getX = (dayIndex) => {
                            const ratio = Math.min(1.0, Math.max(0.0, dayIndex / numDays));
                            return 55 + ratio * 670;
                          };

                          const getY = (val) => {
                            if (val === null || val === undefined) return 225;
                            const r = Math.min(1.0, Math.max(0.0, val / maxVal));
                            return 225 - r * 190;
                          };

                          // Unique Integer Y-Axis Ticks
                          const yTickValues = [];
                          const targetCount = Math.min(5, maxVal + 1);
                          for (let i = 0; i < targetCount; i++) {
                            const v = Math.round((maxVal * i) / (targetCount - 1));
                            if (!yTickValues.includes(v)) {
                              yTickValues.push(v);
                            }
                          }
                          if (!yTickValues.includes(0)) yTickValues.unshift(0);

                          // Collision-Free Evenly-Spaced Milestone Days on X-Axis
                          let dayStep = 1;
                          if (numDays > 30) dayStep = 7;
                          else if (numDays > 16) dayStep = 4;
                          else if (numDays > 8) dayStep = 2;
                          else if (numDays > 4) dayStep = 1;
                          else dayStep = 1;

                          const milestoneDays = [];
                          for (let d = 0; d <= numDays; d += dayStep) {
                            milestoneDays.push(d);
                          }
                          if (milestoneDays[milestoneDays.length - 1] !== numDays) {
                            const last = milestoneDays[milestoneDays.length - 1];
                            if (numDays - last < dayStep * 0.5 && milestoneDays.length > 1) {
                              milestoneDays[milestoneDays.length - 1] = numDays;
                            } else {
                              milestoneDays.push(numDays);
                            }
                          }

                          // Ideal linear path from (0, maxVal) to (numDays, 0)
                          const idealPath = `M 55 ${getY(maxVal)} L 725 ${getY(0)}`;

                          // Actual path across recorded events
                          const actualEntries = points.filter((d) => d.actual_remaining !== null);
                          const actualPath = actualEntries
                            .map((d, idx) => `${idx === 0 ? 'M' : 'L'} ${getX(d.day_index)} ${getY(d.actual_remaining)}`)
                            .join(' ');

                          // Gradient Area under actual line
                          let areaPath = '';
                          if (actualEntries.length > 0) {
                            const firstX = getX(actualEntries[0].day_index);
                            const lastX = getX(actualEntries[actualEntries.length - 1].day_index);
                            areaPath = `${actualPath} L ${lastX} 225 L ${firstX} 225 Z`;
                          }

                          // Live Current Checkpoint
                          const liveEntry = points.find((d) => d.is_live);
                          const liveX = liveEntry ? getX(liveEntry.day_index) : null;

                          return (
                            <>
                              {/* Horizontal Grid Lines & Y-Axis Numbers */}
                              {yTickValues.map((val, idx) => {
                                const yPos = getY(val);
                                return (
                                  <g key={`y-${idx}`}>
                                    <line
                                      x1="55"
                                      y1={yPos}
                                      x2="725"
                                      y2={yPos}
                                      stroke="var(--border)"
                                      strokeWidth="1"
                                      strokeDasharray={val === 0 ? "none" : "3 3"}
                                      opacity={val === 0 ? 0.9 : 0.45}
                                    />
                                    <text
                                      x="46"
                                      y={yPos + 4}
                                      textAnchor="end"
                                      fill="var(--text-muted)"
                                      fontSize="10.5"
                                      fontFamily="monospace"
                                      fontWeight="600"
                                    >
                                      {val}
                                    </text>
                                  </g>
                                );
                              })}

                              {/* Milestone Days Vertical Guides & Clean X-Axis Labels */}
                              {milestoneDays.map((dayIdx, idx) => {
                                const px = getX(dayIdx);
                                const startDate = selectedSprint?.start_date ? new Date(selectedSprint.start_date) : new Date();
                                const tickDate = new Date(startDate.getTime() + dayIdx * 86400000);
                                const dateLabel = tickDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

                                return (
                                  <g key={`x-${idx}`}>
                                    <line x1={px} y1="32" x2={px} y2="225" stroke="var(--border)" strokeWidth="1" strokeDasharray="3 4" opacity="0.3" />
                                    <line x1={px} y1="225" x2={px} y2="231" stroke="var(--border)" strokeWidth="1.5" />
                                    <text x={px} y="246" textAnchor="middle" fill="var(--text)" fontSize="10.5" fontWeight="600">
                                      {dateLabel}
                                    </text>
                                    <text x={px} y="260" textAnchor="middle" fill="var(--text-muted)" fontSize="9" fontFamily="monospace">
                                      Day {dayIdx}
                                    </text>
                                  </g>
                                );
                              })}

                              {/* Live Timestamp Vertical Accent Marker */}
                              {liveX !== null && (
                                <g>
                                  <line x1={liveX} y1="32" x2={liveX} y2="225" stroke="#38bdf8" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.5" />
                                  <rect x={liveX - 18} y="10" width="36" height="15" rx="4" fill="rgba(56, 189, 248, 0.15)" stroke="#38bdf8" strokeWidth="1" />
                                  <text x={liveX} y="21" textAnchor="middle" fill="#38bdf8" fontSize="8.5" fontWeight="800" letterSpacing="0.5px">
                                    NOW
                                  </text>
                                </g>
                              )}

                              {/* Ideal Guideline */}
                              <path d={idealPath} fill="none" stroke="#94a3b8" strokeWidth="2" strokeDasharray="6 4" opacity="0.75" />

                              {/* Actual Progression Gradient Area */}
                              {areaPath && <path d={areaPath} fill="url(#burndownGradPrecise)" />}

                              {/* Actual Progression Solid Vector */}
                              {actualEntries.length > 0 && (
                                <path
                                  d={actualPath}
                                  fill="none"
                                  stroke="var(--accent)"
                                  strokeWidth="3.5"
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                />
                              )}

                              {/* Interactive Data Point Markers */}
                              {actualEntries.map((d, idx) => {
                                const px = getX(d.day_index);
                                const py = getY(d.actual_remaining);
                                const isLive = d.is_live;

                                return (
                                  <g
                                    key={`pt-${idx}`}
                                    style={{ cursor: 'pointer' }}
                                    onMouseEnter={() => setHoveredPoint({ ...d, x: px, y: py })}
                                  >
                                    {/* Transparent larger hover hit box */}
                                    <circle cx={px} cy={py} r="14" fill="transparent" />

                                    {/* Outer ripple for live point */}
                                    {isLive && (
                                      <circle cx={px} cy={py} r="10" fill="var(--accent)" opacity="0.35" />
                                    )}

                                    <circle
                                      cx={px}
                                      cy={py}
                                      r={isLive ? 6 : 4.5}
                                      fill={isLive ? '#38bdf8' : 'var(--accent)'}
                                      stroke="var(--surface)"
                                      strokeWidth="2.5"
                                    />
                                  </g>
                                );
                              })}
                            </>
                          );
                        })()}
                      </svg>

                      {/* Interactive Floating Tooltip */}
                      {hoveredPoint && (
                        <div
                          style={{
                            position: 'absolute',
                            left: `${Math.min(80, Math.max(20, (hoveredPoint.x / 760) * 100))}%`,
                            top: `${Math.max(10, (hoveredPoint.y / 290) * 100 - 10)}%`,
                            transform: 'translate(-50%, -100%)',
                            background: 'var(--surface)',
                            border: '1px solid var(--accent)',
                            borderRadius: '8px',
                            padding: '0.65rem 0.85rem',
                            boxShadow: '0 8px 24px rgba(0,0,0,0.35)',
                            pointerEvents: 'none',
                            zIndex: 10,
                            minWidth: '210px',
                            backdropFilter: 'blur(8px)',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                            <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--accent)' }}>
                              {hoveredPoint.is_live ? '● Current Moment' : hoveredPoint.date}
                            </span>
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                              Day {hoveredPoint.day_index}
                            </span>
                          </div>

                          <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text)', margin: '0.2rem 0' }}>
                            {hoveredPoint.actual_remaining} Defects Remaining
                          </div>

                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                            <span>Ideal Pace: {hoveredPoint.ideal_remaining}</span>
                            <span style={{ color: hoveredPoint.actual_remaining <= hoveredPoint.ideal_remaining ? 'var(--success)' : 'var(--warning)', fontWeight: 600 }}>
                              {hoveredPoint.actual_remaining <= hoveredPoint.ideal_remaining ? 'On Track ✓' : 'Behind Pace ⚠️'}
                            </span>
                          </div>

                          {hoveredPoint.event_label && (
                            <div style={{ marginTop: '0.35rem', paddingTop: '0.35rem', borderTop: '1px solid var(--border)', fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                              ⚡ {hoveredPoint.event_label}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No burndown history recorded for this sprint.
                    </div>
                  )}

                  {/* ── Intraday Event & Defect Resolution Timeline Ledger ── */}
                  <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border)', paddingTop: '1.25rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text)' }}>
                        Intraday Defect Resolution Ledger
                      </span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        Micro-level event trail for this milestone
                      </span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '220px', overflowY: 'auto' }}>
                      {metrics.burndown && metrics.burndown.filter((d) => d.actual_remaining !== null).length > 0 ? (
                        metrics.burndown
                          .filter((d) => d.actual_remaining !== null)
                          .map((ev, idx) => (
                            <div
                              key={idx}
                              style={{
                                background: ev.is_live ? 'var(--accent-light)' : 'var(--bg-dark-accent)',
                                border: `1px solid ${ev.is_live ? 'var(--accent)' : 'var(--border)'}`,
                                borderRadius: '6px',
                                padding: '0.6rem 0.85rem',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                fontSize: '0.8rem',
                                gap: '1rem',
                              }}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1, minWidth: 0 }}>
                                <span style={{ fontWeight: 700, color: ev.is_live ? 'var(--accent)' : 'var(--text-muted)', fontFamily: 'monospace', fontSize: '0.75rem', minWidth: '135px' }}>
                                  {ev.date}
                                </span>
                                <span style={{ fontWeight: 600, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                  {ev.event_label || 'Sprint Progress Checkpoint'}
                                </span>
                              </div>

                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
                                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                                  Remaining: <strong>{ev.actual_remaining}</strong> (Ideal: {ev.ideal_remaining})
                                </span>
                                {ev.is_live && (
                                  <span className="badge" style={{ background: 'var(--accent)', color: '#fff', fontSize: '0.65rem', padding: '0.15rem 0.45rem', fontWeight: 700 }}>
                                    LIVE NOW
                                  </span>
                                )}
                              </div>
                            </div>
                          ))
                      ) : (
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No resolution events recorded yet.</div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Developer Workload Allocation */}
              {metrics && metrics.workload && (
                <div
                  style={{
                    background: 'var(--surface)',
                    borderRadius: 'var(--radius)',
                    border: '1px solid var(--border)',
                    padding: '1.5rem',
                    boxShadow: 'var(--shadow-soft)',
                  }}
                >
                  <h3 style={{ margin: '0 0 1rem', fontSize: '1.05rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <User size={18} className="text-accent" /> Developer Capacity & Allocation
                  </h3>

                  {metrics.workload.length === 0 ? (
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                      No developers assigned to issues in this sprint.
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                      {metrics.workload.map((dev, idx) => (
                        <div
                          key={idx}
                          style={{
                            background: 'var(--bg-dark-accent)',
                            border: '1px solid var(--border)',
                            borderRadius: '8px',
                            padding: '1rem',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontWeight: 700, fontSize: '0.9rem' }}>
                              <div
                                style={{
                                  width: '24px',
                                  height: '24px',
                                  borderRadius: '50%',
                                  background: 'var(--accent-light)',
                                  color: 'var(--accent)',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  fontSize: '0.75rem',
                                }}
                              >
                                {dev.username[0]?.toUpperCase()}
                              </div>
                              <span>{dev.username}</span>
                            </div>

                            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent)' }}>
                              {dev.resolved}/{dev.total} Resolved
                            </span>
                          </div>

                          <div style={{ height: '6px', background: 'var(--border)', borderRadius: '3px', overflow: 'hidden', margin: '0.5rem 0' }}>
                            <div
                              style={{
                                height: '100%',
                                width: `${dev.total > 0 ? (dev.resolved / dev.total) * 100 : 0}%`,
                                background: 'var(--success)',
                              }}
                            />
                          </div>

                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            <span>{dev.open} Active / In Progress</span>
                            <span>{dev.total > 0 ? Math.round((dev.resolved / dev.total) * 100) : 0}% completed</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── SUB-TAB 4: AI SPRINT COPILOT ────────────────────────── */}
          {activeTab === 'ai_copilot' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div
                style={{
                  background: 'linear-gradient(135deg, rgba(2, 132, 199, 0.08), rgba(99, 102, 241, 0.08))',
                  border: '1px solid var(--accent)',
                  borderRadius: 'var(--radius)',
                  padding: '1.25rem 1.5rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '1rem',
                }}
              >
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent)' }}>
                    <Sparkles size={18} /> AI Sprint Intelligence Copilot
                  </h3>
                  <p style={{ margin: '0.2rem 0 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    Automated defect risk prediction, retrospective summaries, and workload capacity recommendations.
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-ai btn-sm"
                    onClick={handleRunAiHealth}
                    disabled={aiLoading.health}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                  >
                    <Activity size={14} /> {aiLoading.health ? 'Analyzing...' : 'Run Health Check'}
                  </button>

                  <button
                    className="btn btn-ai btn-sm"
                    onClick={handleRunAiRetro}
                    disabled={aiLoading.retro}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                  >
                    <FileText size={14} /> {aiLoading.retro ? 'Generating...' : 'Sprint Retrospective'}
                  </button>

                  <button
                    className="btn btn-ai btn-sm"
                    onClick={handleRunAiAdvisor}
                    disabled={aiLoading.advisor}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                  >
                    <Zap size={14} /> {aiLoading.advisor ? 'Evaluating...' : 'Scope Advisor'}
                  </button>
                </div>
              </div>

              {/* 1. Health Card */}
              {aiHealth && (
                <div
                  style={{
                    background: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius)',
                    padding: '1.25rem 1.5rem',
                    boxShadow: 'var(--shadow-soft)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                      <Activity size={16} className="text-accent" /> Sprint Health Assessment
                    </h4>
                    <span
                      className="badge"
                      style={{
                        background: aiHealth.risk_level === 'Low' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                        color: aiHealth.risk_level === 'Low' ? 'var(--success)' : 'var(--danger)',
                        fontWeight: 700,
                      }}
                    >
                      Risk: {aiHealth.risk_level} ({aiHealth.health_score}/100)
                    </span>
                  </div>

                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                    Open: {aiHealth.open_issues_count} | Resolved: {aiHealth.resolved_issues_count} | Critical Blockers: {aiHealth.critical_issues_count}
                  </div>

                  {aiHealth.recommendations?.length > 0 && (
                    <div style={{ background: 'var(--bg-dark-accent)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                      <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text)', marginBottom: '0.35rem' }}>Recommendations:</div>
                      <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        {aiHealth.recommendations.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* 2. Retrospective Card */}
              {aiRetro && (
                <div
                  style={{
                    background: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius)',
                    padding: '1.25rem 1.5rem',
                    boxShadow: 'var(--shadow-soft)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                    <h4 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                      <FileText size={16} className="text-accent" /> AI Retrospective Summary
                    </h4>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {aiRetro.velocity_score !== undefined && (
                        <span className="badge" style={{ background: 'var(--accent-light)', color: 'var(--accent)', fontWeight: 700, fontSize: '0.75rem' }}>
                          ⚡ Velocity Score: {aiRetro.velocity_score}/100
                        </span>
                      )}
                      {aiRetro.completion_rate !== undefined && (
                        <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: 'var(--success)', fontWeight: 700, fontSize: '0.75rem' }}>
                          🎯 Delivery: {Math.round(aiRetro.completion_rate * 100)}%
                        </span>
                      )}
                    </div>
                  </div>

                  {aiRetro.summary && (
                    <div style={{ background: 'var(--bg-dark-accent)', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid var(--border)', marginBottom: '1rem', fontSize: '0.85rem', color: 'var(--text)', lineHeight: 1.5 }}>
                      {aiRetro.summary}
                    </div>
                  )}

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
                    {(aiRetro.highlights || aiRetro.went_well) && (
                      <div style={{ background: 'var(--bg-dark-accent)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                        <div style={{ fontWeight: 700, color: 'var(--success)', fontSize: '0.85rem', marginBottom: '0.4rem' }}>
                          🌟 Delivery Highlights & Successes
                        </div>
                        <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                          {(aiRetro.highlights || aiRetro.went_well).map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {aiRetro.blockers && aiRetro.blockers.length > 0 && (
                      <div style={{ background: 'var(--bg-dark-accent)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                        <div style={{ fontWeight: 700, color: 'var(--danger)', fontSize: '0.85rem', marginBottom: '0.4rem' }}>
                          ⚠️ Blockers & Friction
                        </div>
                        <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                          {aiRetro.blockers.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {aiRetro.risk_drivers && aiRetro.risk_drivers.length > 0 && (
                      <div style={{ background: 'var(--bg-dark-accent)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                        <div style={{ fontWeight: 700, color: 'var(--warning)', fontSize: '0.85rem', marginBottom: '0.4rem' }}>
                          🔍 Risk Drivers & Skew
                        </div>
                        <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                          {aiRetro.risk_drivers.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {aiRetro.action_items && aiRetro.action_items.length > 0 && (
                      <div style={{ background: 'var(--bg-dark-accent)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
                        <div style={{ fontWeight: 700, color: 'var(--accent)', fontSize: '0.85rem', marginBottom: '0.4rem' }}>
                          🎯 Next Sprint Action Items
                        </div>
                        <ul style={{ margin: 0, paddingLeft: '1.1rem', fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                          {aiRetro.action_items.map((item, i) => (
                            <li key={i}>{item}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 3. Scope Advisor Card */}
              {aiAdvisor && (
                <div
                  style={{
                    background: 'var(--surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius)',
                    padding: '1.25rem 1.5rem',
                    boxShadow: 'var(--shadow-soft)',
                  }}
                >
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                    <Zap size={16} className="text-accent" /> Capacity & Scope Guidance
                  </h4>
                  <p style={{ margin: '0 0 0.75rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    {aiAdvisor.summary || aiAdvisor.overview}
                  </p>

                  {aiAdvisor.recommendations?.length > 0 && (
                    <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {aiAdvisor.recommendations.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── SUB-TAB 5: MILESTONES & ARCHIVE ─────────────────────── */}
          {activeTab === 'archive' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {completedSprints.length === 0 ? (
                <div
                  style={{
                    background: 'var(--surface)',
                    border: '1px dashed var(--border)',
                    borderRadius: 'var(--radius)',
                    padding: '3rem',
                    textAlign: 'center',
                    color: 'var(--text-muted)',
                  }}
                >
                  <FileText size={36} style={{ marginBottom: '0.75rem' }} />
                  <h4 style={{ margin: '0 0 0.5rem', fontWeight: 700 }}>No Completed Sprints Yet</h4>
                  <p style={{ fontSize: '0.85rem' }}>
                    When you finish an active iteration, complete it to archive the sprint velocity and performance metrics.
                  </p>
                </div>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
                  {completedSprints.map((sprint) => (
                    <div
                      key={sprint.id}
                      style={{
                        background: 'var(--surface)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius)',
                        padding: '1.25rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.75rem',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <h4 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700 }}>{sprint.name}</h4>
                          {sprint.goal && <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: 'var(--text-muted)' }}>{sprint.goal}</p>}
                        </div>
                        <span className="badge badge-completed" style={{ textTransform: 'uppercase', fontSize: '0.7rem' }}>
                          Completed
                        </span>
                      </div>

                      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border)', paddingTop: '0.65rem' }}>
                        {sprint.start_date && <span>Start: {new Date(sprint.start_date).toLocaleDateString()}</span>}
                        {sprint.end_date && <span>Closed: {new Date(sprint.end_date).toLocaleDateString()}</span>}
                      </div>

                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ alignSelf: 'flex-start' }}
                        onClick={() => {
                          setSelectedSprintId(sprint.id);
                          setActiveTab('analytics');
                        }}
                      >
                        View Velocity & Metrics
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* ── MODAL: CREATE SPRINT ──────────────────────────────────────── */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
                <Zap size={18} />
              </div>
              <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800 }}>Create Agile Sprint</h2>
            </div>

            <form onSubmit={handleCreateSprint} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="form-group">
                <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Sprint Name *</label>
                <input
                  value={sprintForm.name}
                  onChange={(e) => setSprintForm((p) => ({ ...p, name: e.target.value }))}
                  placeholder="e.g. Sprint 15 - Performance & Core Engine"
                  required
                />
              </div>

              <div className="form-group">
                <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Sprint Objective / Goal</label>
                <textarea
                  value={sprintForm.goal}
                  onChange={(e) => setSprintForm((p) => ({ ...p, goal: e.target.value }))}
                  placeholder="Primary targets, deliverables, and critical defect targets..."
                  rows={2}
                />
              </div>

              <div className="form-group">
                <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Duration Quick Presets</label>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => applyDurationPreset(1)}>
                    1 Week
                  </button>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => applyDurationPreset(2)}>
                    2 Weeks
                  </button>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => applyDurationPreset(3)}>
                    3 Weeks
                  </button>
                  <button type="button" className="btn btn-secondary btn-sm" onClick={() => applyDurationPreset(4)}>
                    1 Month
                  </button>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div className="form-group">
                  <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Start Date</label>
                  <input
                    type="date"
                    value={sprintForm.start_date}
                    onChange={(e) => setSprintForm((p) => ({ ...p, start_date: e.target.value }))}
                  />
                </div>
                <div className="form-group">
                  <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Target End Date</label>
                  <input
                    type="date"
                    value={sprintForm.end_date}
                    onChange={(e) => setSprintForm((p) => ({ ...p, end_date: e.target.value }))}
                  />
                </div>
              </div>

              <div className="modal-actions" style={{ marginTop: '0.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create Sprint Milestone
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: EDIT SPRINT ────────────────────────────────────────── */}
      {showEditModal && (
        <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
            <h2 style={{ margin: '0 0 1rem', fontSize: '1.2rem', fontWeight: 800 }}>Edit Sprint Milestone</h2>

            <form onSubmit={handleUpdateSprint} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="form-group">
                <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Sprint Name *</label>
                <input
                  value={sprintForm.name}
                  onChange={(e) => setSprintForm((p) => ({ ...p, name: e.target.value }))}
                  required
                />
              </div>

              <div className="form-group">
                <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Sprint Objective / Goal</label>
                <textarea
                  value={sprintForm.goal}
                  onChange={(e) => setSprintForm((p) => ({ ...p, goal: e.target.value }))}
                  rows={2}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div className="form-group">
                  <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Start Date</label>
                  <input
                    type="date"
                    value={sprintForm.start_date}
                    onChange={(e) => setSprintForm((p) => ({ ...p, start_date: e.target.value }))}
                  />
                </div>
                <div className="form-group">
                  <label style={{ fontWeight: 600, fontSize: '0.85rem' }}>Target End Date</label>
                  <input
                    type="date"
                    value={sprintForm.end_date}
                    onChange={(e) => setSprintForm((p) => ({ ...p, end_date: e.target.value }))}
                  />
                </div>
              </div>

              <div className="modal-actions" style={{ marginTop: '0.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── MODAL: COMPLETE SPRINT & ROLLOVER ─────────────────────────── */}
      {showCompleteModal && (
        <div className="modal-overlay" onClick={() => setShowCompleteModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <CheckCircle2 size={22} style={{ color: 'var(--success)' }} />
              <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800 }}>Complete Sprint</h2>
            </div>

            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: '0 0 1rem' }}>
              You are completing <strong>{selectedSprint?.name}</strong>. Choose how to handle any open or unresolved defects.
            </p>

            {metrics && (
              <div
                style={{
                  background: 'var(--bg-dark-accent)',
                  padding: '0.75rem 1rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                  marginBottom: '1rem',
                  fontSize: '0.85rem',
                }}
              >
                <div>
                  <strong>Resolved:</strong> {metrics.resolved_issues + metrics.closed_issues} / {metrics.total_issues} defects
                </div>
                <div style={{ color: metrics.open_issues + metrics.in_progress_issues > 0 ? 'var(--warning)' : 'var(--success)', marginTop: '0.25rem' }}>
                  <strong>Unresolved:</strong> {metrics.open_issues + metrics.in_progress_issues + metrics.in_review_issues} defects
                </div>
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.25rem' }}>
              {planningSprints.filter((s) => s.id !== selectedSprintId).length > 0 && (
                <label
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.65rem',
                    background: 'var(--surface)',
                    padding: '0.65rem 0.85rem',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    cursor: 'pointer',
                  }}
                >
                  <input
                    type="radio"
                    name="completeOption"
                    value="rollover"
                    checked={completeOption === 'rollover'}
                    onChange={() => setCompleteOption('rollover')}
                    style={{ marginTop: '0.2rem' }}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>Roll over open defects to next sprint:</div>
                    <select
                      value={rolloverTargetId}
                      onChange={(e) => setRolloverTargetId(e.target.value)}
                      disabled={completeOption !== 'rollover'}
                      style={{
                        width: '100%',
                        marginTop: '0.4rem',
                        padding: '0.35rem 0.65rem',
                        borderRadius: '6px',
                        border: '1px solid var(--border)',
                        background: 'var(--bg-dark-accent)',
                        color: 'var(--text)',
                        fontSize: '0.8rem',
                      }}
                    >
                      {planningSprints
                        .filter((s) => s.id !== selectedSprintId)
                        .map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.name}
                          </option>
                        ))}
                    </select>
                  </div>
                </label>
              )}

              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.65rem',
                  background: 'var(--surface)',
                  padding: '0.65rem 0.85rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="radio"
                  name="completeOption"
                  value="backlog"
                  checked={completeOption === 'backlog'}
                  onChange={() => setCompleteOption('backlog')}
                />
                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Move open defects to the Project Backlog</span>
              </label>

              <label
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.65rem',
                  background: 'var(--surface)',
                  padding: '0.65rem 0.85rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="radio"
                  name="completeOption"
                  value="keep"
                  checked={completeOption === 'keep'}
                  onChange={() => setCompleteOption('keep')}
                />
                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Keep defect assignments as they are</span>
              </label>
            </div>

            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={() => setShowCompleteModal(false)}>
                Cancel
              </button>
              <button type="button" className="btn btn-primary" onClick={handleConfirmCompleteSprint}>
                Confirm Sprint Completion
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
