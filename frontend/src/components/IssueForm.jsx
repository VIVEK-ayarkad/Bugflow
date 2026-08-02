import { useEffect, useState } from 'react';
import { Bot, Sparkles, Mic, Search, AlertTriangle, Info } from 'lucide-react';
import { aiAssist, aiDetectDuplicates, aiPredictSeverity, getSprints, getUsers } from '../api';

const EMPTY = {
  title: '',
  description: '',
  steps_to_reproduce: '',
  expected_behavior: '',
  actual_behavior: '',
  severity: 'medium',
  priority: 'medium',
  status: 'open',
  assigned_developer_id: '',
  sprint_id: '',
  os: '',
  browser: '',
};

const PROMPT_SUGGESTIONS = [
  'Login button unresponsive on Chrome',
  'API 500 error during checkout',
  'Profile image upload fails on mobile',
  'Slow query response when loading metrics',
];

export default function IssueForm({
  initial,
  onSubmit,
  onCancel,
  submitLabel = 'Save Issue',
  projectId = null,
}) {
  const [form, setForm] = useState({ ...EMPTY, ...initial });
  const [rawInput, setRawInput] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState(null);
  const [severityPredicting, setSeverityPredicting] = useState(false);
  const [severityRationale, setSeverityRationale] = useState('');
  const [duplicates, setDuplicates] = useState([]);
  const [detectingDuplicates, setDetectingDuplicates] = useState(false);
  const [developers, setDevelopers] = useState([]);
  const [sprints, setSprints] = useState([]);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [isListening, setIsListening] = useState(false);

  useEffect(() => {
    loadOptions();
  }, [projectId]);

  async function loadOptions() {
    try {
      const usersData = await getUsers();
      setDevelopers(usersData.filter((u) => u.role === 'developer' || u.role === 'admin' || u.role === 'project_manager'));

      if (projectId) {
        const sprintsData = await getSprints(projectId);
        setSprints(sprintsData);
      }
    } catch {
      // ignore non-critical load options error
    }
  }

  const set = (field, value) => setForm((f) => ({ ...f, [field]: value }));

  const autoPredictSeverity = async (titleToUse, descToUse) => {
    const t = titleToUse !== undefined ? titleToUse : form.title;
    const d = descToUse !== undefined ? descToUse : form.description;
    if (!t.trim() && !d.trim()) return;

    setSeverityPredicting(true);
    try {
      const res = await aiPredictSeverity(t, d);
      if (res.predicted_severity) {
        set('severity', res.predicted_severity);
        setSeverityRationale(res.rationale);
      }
    } catch {
      // silent ignore
    } finally {
      setSeverityPredicting(false);
    }
  };

  const handleDetectDuplicates = async () => {
    if (!projectId || !form.title) return;
    setDetectingDuplicates(true);
    try {
      const res = await aiDetectDuplicates(projectId, form.title, form.description);
      setDuplicates(res.potential_duplicates || []);
    } catch {
      setDuplicates([]);
    } finally {
      setDetectingDuplicates(false);
    }
  };

  const toggleVoiceDictation = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      const sampleVoiceText = "User receives 500 internal server error when updating billing address on chrome desktop.";
      setRawInput(sampleVoiceText);
      handleAiAssist(sampleVoiceText);
      return;
    }

    if (isListening) {
      setIsListening(false);
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => setIsListening(false);

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setRawInput(transcript);
          handleAiAssist(transcript);
        }
      };

      recognition.start();
    } catch {
      setIsListening(false);
    }
  };

  const handleAiAssist = async (inputOverride) => {
    const textToUse = typeof inputOverride === 'string' ? inputOverride : (rawInput.trim() || form.description.trim());
    if (!textToUse) return;
    setAiLoading(true);
    setAiResult(null);
    try {
      const result = await aiAssist(textToUse);
      setAiResult(result);
      if (result.formatted_report) {
        const r = result.formatted_report;
        const newTitle = r.title || form.title;
        const newDesc = r.description || form.description;
        setForm((f) => ({
          ...f,
          title: newTitle,
          description: newDesc,
          priority: r.priority || f.priority,
        }));
        autoPredictSeverity(newTitle, newDesc);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setAiLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      const payload = {
        ...form,
        assigned_developer_id: form.assigned_developer_id ? parseInt(form.assigned_developer_id) : null,
        sprint_id: form.sprint_id ? parseInt(form.sprint_id) : null,
      };
      await onSubmit(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="issue-form">
      <div className="ai-panel">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Sparkles size={16} /> AI Copilot & Voice Dictation
          </h3>
          <button
            type="button"
            className={`voice-record-btn ${isListening ? 'recording' : ''}`}
            onClick={toggleVoiceDictation}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
          >
            <Mic size={14} />
            {isListening ? 'Listening…' : 'Voice Bug Report'}
          </button>
        </div>

        <p style={{ fontSize: '0.83rem', color: 'var(--text-muted)', marginTop: '0.4rem', marginBottom: '0.5rem' }}>
          Describe the defect briefly or use dictation to automatically format steps & reproduction notes.
        </p>

        <div className="prompt-chips">
          {PROMPT_SUGGESTIONS.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              className="prompt-chip"
              onClick={() => {
                setRawInput(chip);
                handleAiAssist(chip);
              }}
            >
              + {chip}
            </button>
          ))}
        </div>

        <div className="form-group" style={{ marginBottom: '0.75rem' }}>
          <textarea
            value={rawInput}
            onChange={(e) => setRawInput(e.target.value)}
            placeholder="e.g. login fails on safari with 401 unhandled error"
            rows={2}
          />
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            type="button"
            className="btn btn-ai btn-sm"
            onClick={() => handleAiAssist()}
            disabled={aiLoading || (!rawInput.trim() && !form.description.trim())}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
          >
            <Sparkles size={14} />
            {aiLoading ? 'Formatting...' : 'Auto-Generate Bug Report'}
          </button>
        </div>
      </div>

      <div className="form-group">
        <label>Issue Title *</label>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            value={form.title}
            onChange={(e) => set('title', e.target.value)}
            onBlur={() => {
              handleDetectDuplicates();
              autoPredictSeverity();
            }}
            placeholder="e.g. Authentication failure on login submission"
            required
            style={{ flex: 1 }}
          />
          {projectId && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleDetectDuplicates}
              disabled={detectingDuplicates || !form.title}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <Search size={13} /> Scan Duplicates
            </button>
          )}
        </div>
      </div>

      {duplicates.length > 0 && (
        <div className="duplicate-panel" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #f87171', padding: '0.75rem', borderRadius: '8px', marginBottom: '1rem' }}>
          <h4 style={{ color: '#f87171', margin: 0, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <AlertTriangle size={15} /> Potential Duplicate Bugs Detected
          </h4>
          <ul style={{ margin: '0.5rem 0 0 1.2rem', fontSize: '0.85rem' }}>
            {duplicates.map((dup) => (
              <li key={dup.id}>
                <strong>#{dup.id} {dup.title}</strong> — Status: <em>{dup.status}</em> (Score: {dup.similarity_score}%)
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="form-group">
        <label>Summary Description *</label>
        <textarea
          value={form.description}
          onChange={(e) => set('description', e.target.value)}
          onBlur={() => autoPredictSeverity()}
          placeholder="Brief summary of the issue..."
          required
          rows={3}
        />
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Steps to Reproduce</label>
          <textarea
            value={form.steps_to_reproduce || ''}
            onChange={(e) => set('steps_to_reproduce', e.target.value)}
            placeholder="1. Go to page... 2. Click button..."
            rows={2}
          />
        </div>
        <div className="form-group">
          <label>Expected vs Actual Result</label>
          <textarea
            value={form.expected_behavior || ''}
            onChange={(e) => set('expected_behavior', e.target.value)}
            placeholder="Expected behavior..."
            rows={2}
          />
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <label>Severity</label>
            {severityPredicting ? (
              <span style={{ fontSize: '0.75rem', color: 'var(--accent)', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                <Sparkles size={12} /> Auto-predicting severity…
              </span>
            ) : (
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                <Sparkles size={11} color="var(--accent)" /> AI Auto-Assigned
              </span>
            )}
          </div>
          <select value={form.severity} onChange={(e) => set('severity', e.target.value)}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          {severityRationale && (
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
              <Info size={12} /> {severityRationale}
            </p>
          )}
        </div>

        <div className="form-group">
          <label>Priority</label>
          <select value={form.priority} onChange={(e) => set('priority', e.target.value)}>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>

        <div className="form-group">
          <label>Workflow Status</label>
          <select value={form.status} onChange={(e) => set('status', e.target.value)}>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="in_review">In Review</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Assigned Developer</label>
          <select
            value={form.assigned_developer_id || ''}
            onChange={(e) => set('assigned_developer_id', e.target.value)}
          >
            <option value="">-- Unassigned --</option>
            {developers.map((dev) => (
              <option key={dev.id} value={dev.id}>
                {dev.username} ({dev.role})
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>Sprint</label>
          <select value={form.sprint_id || ''} onChange={(e) => set('sprint_id', e.target.value)}>
            <option value="">-- No Sprint (Backlog) --</option>
            {sprints.map((sp) => (
              <option key={sp.id} value={sp.id}>
                {sp.name} ({sp.status})
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="error" style={{ marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      <div className="modal-actions">
        <button type="button" className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="btn btn-primary" disabled={saving}>
          {saving ? 'Saving...' : submitLabel}
        </button>
      </div>
    </form>
  );
}
