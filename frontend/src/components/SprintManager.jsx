import { useEffect, useState } from 'react';
import { Zap, Play, CheckCircle2, Sparkles, Plus } from 'lucide-react';
import { aiSprintHealth, completeSprint, createSprint, getSprints, startSprint } from '../api';

export default function SprintManager({ projectId, onRefresh }) {
  const [sprints, setSprints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNewModal, setShowNewModal] = useState(false);
  const [newSprintName, setNewSprintName] = useState('');
  const [newSprintGoal, setNewSprintGoal] = useState('');
  const [healthMap, setHealthMap] = useState({});

  useEffect(() => {
    if (projectId) loadSprints();
  }, [projectId]);

  async function loadSprints() {
    setLoading(true);
    try {
      const data = await getSprints(projectId);
      setSprints(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateSprint(e) {
    e.preventDefault();
    if (!newSprintName.trim()) return;
    try {
      await createSprint(projectId, { name: newSprintName, goal: newSprintGoal });
      setNewSprintName('');
      setNewSprintGoal('');
      setShowNewModal(false);
      loadSprints();
      onRefresh();
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleStartSprint(sprintId) {
    try {
      await startSprint(sprintId);
      loadSprints();
      onRefresh();
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleCompleteSprint(sprintId) {
    try {
      await completeSprint(sprintId);
      loadSprints();
      onRefresh();
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleAnalyzeHealth(sprintId) {
    try {
      const res = await aiSprintHealth(sprintId);
      setHealthMap((prev) => ({ ...prev, [sprintId]: res }));
    } catch (err) {
      alert(err.message);
    }
  }

  return (
    <div className="sprint-manager">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Zap size={22} className="text-accent" /> Sprint Management
        </h2>
        <button className="btn btn-primary" onClick={() => setShowNewModal(true)} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
          <Plus size={16} /> Create Sprint
        </button>
      </div>

      {loading ? (
        <div>Loading Sprints...</div>
      ) : sprints.length === 0 ? (
        <div className="empty-state">No sprints created for this project yet.</div>
      ) : (
        <div className="sprints-grid">
          {sprints.map((sprint) => {
            const health = healthMap[sprint.id];

            return (
              <div key={sprint.id} className="sprint-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h3>{sprint.name}</h3>
                    {sprint.goal && <p className="sprint-goal">{sprint.goal}</p>}
                  </div>
                  <span className={`badge badge-${sprint.status}`}>{sprint.status}</span>
                </div>

                <div className="sprint-actions" style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
                  {sprint.status === 'planning' && (
                    <button className="btn btn-primary btn-sm" onClick={() => handleStartSprint(sprint.id)} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                      <Play size={14} /> Start Sprint
                    </button>
                  )}
                  {sprint.status === 'active' && (
                    <button className="btn btn-secondary btn-sm" onClick={() => handleCompleteSprint(sprint.id)} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                      <CheckCircle2 size={14} /> Complete Sprint
                    </button>
                  )}
                  <button className="btn btn-ai btn-sm" onClick={() => handleAnalyzeHealth(sprint.id)} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                    <Sparkles size={14} /> AI Sprint Health
                  </button>
                </div>

                {health && (
                  <div className="sprint-health-widget" style={{ marginTop: '0.75rem', background: 'rgba(15, 23, 42, 0.4)', padding: '0.75rem', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold' }}>
                      <span>Sprint Health Score: {health.health_score}/100</span>
                      <span style={{ color: health.risk_level === 'Low' ? '#34d399' : '#f87171' }}>
                        Risk: {health.risk_level}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
                      Open: {health.open_issues_count} | Resolved: {health.resolved_issues_count} | Critical: {health.critical_issues_count}
                    </div>
                    {health.recommendations?.length > 0 && (
                      <ul style={{ margin: '0.4rem 0 0 1rem', fontSize: '0.8rem' }}>
                        {health.recommendations.map((rec, i) => (
                          <li key={i}>{rec}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {showNewModal && (
        <div className="modal-overlay" onClick={() => setShowNewModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>Create New Sprint</h2>
            <form onSubmit={handleCreateSprint}>
              <div className="form-group">
                <label>Sprint Name</label>
                <input
                  value={newSprintName}
                  onChange={(e) => setNewSprintName(e.target.value)}
                  placeholder="e.g. Sprint 14 - Auth Engine overhaul"
                  required
                />
              </div>
              <div className="form-group">
                <label>Sprint Goal</label>
                <textarea
                  value={newSprintGoal}
                  onChange={(e) => setNewSprintGoal(e.target.value)}
                  placeholder="Goals and targets for this sprint..."
                  rows={2}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowNewModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create Sprint
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
