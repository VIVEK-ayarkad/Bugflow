import { useEffect, useState } from 'react';
import { Bot, Sparkles, Mic, Search, AlertTriangle, Info, CheckCircle2, Layers, Tag, ShieldAlert } from 'lucide-react';
import { aiAssist, aiClassifyDefect, aiDetectDuplicates, aiPredictSeverity, getSprints, getUsers } from '../api';

const EMPTY = {
  title: '',
  description: '',
  steps_to_reproduce: '',
  expected_behavior: '',
  actual_behavior: '',
  category: '',
  module: '',
  defect_type: '',
  severity: 'medium',
  priority: 'medium',
  status: 'open',
  assigned_developer_id: '',
  sprint_id: '',
  os: '',
  browser: '',
};

const PROMPT_SUGGESTIONS = [
  'Application crashes when submitting payment.',
  'All users are unable to complete payment.',
  'Payment page crashes when the user clicks Submit.',
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
  const [classification, setClassification] = useState(null);
  const [classifying, setClassifying] = useState(false);
  const [suggestionAccepted, setSuggestionAccepted] = useState(false);
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

  useEffect(() => {
    if (initial) {
      setForm({ ...EMPTY, ...initial });
    }
  }, [initial]);

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

  const handleClassify = async (descToUse, titleToUse) => {
    const d = descToUse !== undefined ? descToUse : (form.description.trim() || rawInput.trim());
    const t = titleToUse !== undefined ? titleToUse : form.title.trim();
    if (!d && !t) return;

    setClassifying(true);
    try {
      const res = await aiClassifyDefect(d, t);
      setClassification(res);
      setSuggestionAccepted(false);
    } catch {
      // silent ignore
    } finally {
      setClassifying(false);
    }
  };

  const acceptSuggestion = () => {
    if (!classification) return;
    setForm((f) => ({
      ...f,
      category: classification.category || f.category,
      module: classification.module || f.module,
      defect_type: classification.defect_type || f.defect_type,
      severity: classification.suggested_severity || f.severity,
      priority: classification.suggested_priority || f.priority,
    }));
    setSeverityRationale(classification.rationale);
    setSuggestionAccepted(true);
  };

  const autoPredictSeverity = async (titleToUse, descToUse) => {
    const t = titleToUse !== undefined ? titleToUse : form.title;
    const d = descToUse !== undefined ? descToUse : form.description;
    if (!t.trim() && !d.trim()) return;

    setSeverityPredicting(true);
    try {
      const res = await aiPredictSeverity(t, d);
      if (res.predicted_severity) {
        setForm((f) => ({
          ...f,
          severity: res.predicted_severity,
          priority: res.predicted_priority || f.priority,
        }));
        setSeverityRationale(res.rationale);
      }
    } catch {
      // silent ignore
    } finally {
      setSeverityPredicting(false);
    }
  };

  const handleDetectDuplicates = async (titleToUse, descToUse) => {
    if (!projectId) return;
    const t = titleToUse !== undefined ? titleToUse : (form.title.trim() || rawInput.trim());
    const d = descToUse !== undefined ? descToUse : form.description.trim();
    if (!t && !d) return;

    setDetectingDuplicates(true);
    try {
      const res = await aiDetectDuplicates(projectId, t, d);
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
      handleClassify(sampleVoiceText);
      handleDetectDuplicates(sampleVoiceText, "");
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
          handleClassify(transcript);
          handleDetectDuplicates(transcript, "");
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
        handleClassify(newDesc, newTitle);
        handleDetectDuplicates(newTitle, newDesc);
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

        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
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

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => handleClassify()}
            disabled={classifying || (!rawInput.trim() && !form.description.trim() && !form.title.trim())}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
          >
            <Layers size={14} />
            {classifying ? 'Classifying Defect…' : 'Classify Defect & Severity'}
          </button>
        </div>
      </div>

      {/* Intelligent Defect Classification Suggestion Box */}
      {classification && (
        <div className="defect-classification-card" style={{
          background: suggestionAccepted ? 'var(--success-light)' : 'var(--bg-card)',
          border: `1.5px solid ${suggestionAccepted ? 'var(--success-border)' : 'var(--accent)'}`,
          borderRadius: 'var(--radius)',
          padding: '1.1rem',
          marginBottom: '1.25rem',
          boxShadow: 'var(--shadow-sm)',
          transition: 'var(--transition)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', color: suggestionAccepted ? 'var(--success)' : 'var(--accent)', fontWeight: '800', fontSize: '0.92rem' }}>
              <Sparkles size={17} />
              <span>Intelligent Defect Classification Suggestion</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="badge" style={{ background: 'var(--accent-light)', color: 'var(--accent)', borderColor: 'var(--border)', fontSize: '0.72rem' }}>
                Confidence: {(classification.confidence * 100).toFixed(0)}%
              </span>
              {suggestionAccepted && (
                <span className="badge badge-status-resolved" style={{ fontSize: '0.72rem', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                  <CheckCircle2 size={12} /> Accepted & Applied
                </span>
              )}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '0.75rem', marginBottom: '0.85rem' }}>
            <div style={{ background: 'var(--bg-dark-accent)', padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Category</div>
              <div style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text)' }}>{classification.category}</div>
            </div>

            <div style={{ background: 'var(--bg-dark-accent)', padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Module / Component</div>
              <div style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text)' }}>{classification.module}</div>
            </div>

            <div style={{ background: 'var(--bg-dark-accent)', padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Defect Type</div>
              <div style={{ fontSize: '0.9rem', fontWeight: '700', color: 'var(--text)' }}>{classification.defect_type}</div>
            </div>

            <div style={{ background: 'var(--bg-dark-accent)', padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Suggested Severity</div>
              <div>
                <span className={`badge badge-severity-${classification.suggested_severity}`}>
                  {classification.suggested_severity.toUpperCase()}
                </span>
              </div>
            </div>

            <div style={{ background: 'var(--bg-dark-accent)', padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: '700', textTransform: 'uppercase', marginBottom: '0.2rem' }}>Suggested Priority</div>
              <div>
                <span className={`badge badge-priority-${classification.suggested_priority}`}>
                  {classification.suggested_priority.toUpperCase()}
                </span>
              </div>
            </div>
          </div>

          <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginBottom: '0.9rem', lineHeight: '1.45' }}>
            <strong>AI Rationale:</strong> {classification.rationale}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={acceptSuggestion}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <CheckCircle2 size={14} /> {suggestionAccepted ? 'Re-Apply Suggestion' : 'Accept Suggestion'}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setClassification(null)}
            >
              Dismiss
            </button>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginLeft: 'auto' }}>
              You can modify any of the suggested fields below.
            </span>
          </div>
        </div>
      )}

      <div className="form-group">
        <label>Issue Title *</label>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            value={form.title}
            onChange={(e) => set('title', e.target.value)}
            onBlur={() => {
              handleDetectDuplicates();
              autoPredictSeverity();
              handleClassify();
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
        <div className="similar-defect-panel" style={{
          background: 'var(--warning-light)',
          border: '1.5px solid var(--warning-border)',
          padding: '1rem 1.15rem',
          borderRadius: 'var(--radius)',
          marginBottom: '1.25rem',
          boxShadow: 'var(--shadow-sm)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <h4 style={{ color: 'var(--warning)', margin: 0, fontSize: '0.94rem', display: 'flex', alignItems: 'center', gap: '0.45rem', fontWeight: '800' }}>
              <AlertTriangle size={17} /> ⚠️ Similar Defect Found ({duplicates.length})
            </h4>
            <span className="badge" style={{ background: 'var(--bg-card)', color: 'var(--warning)', borderColor: 'var(--warning-border)', fontSize: '0.72rem' }}>
              Duplicate Defect Prevention
            </span>
          </div>

          <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '0 0 0.75rem 0' }}>
            The system searched existing defects and found similar issues in this project. Review these to prevent duplicate defect creation:
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {duplicates.map((dup) => (
              <div key={dup.id} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                background: 'var(--bg-card)',
                padding: '0.6rem 0.85rem',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border)',
                gap: '0.6rem',
                flexWrap: 'wrap'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
                  <span className="bug-id-tag" style={{ fontWeight: '800', background: 'var(--accent-light)', color: 'var(--accent)', borderColor: 'var(--border)' }}>
                    {dup.key || `DEF-${dup.id}`}
                  </span>
                  <strong style={{ fontSize: '0.88rem', color: 'var(--text)' }}>
                    {dup.title}
                  </strong>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span className={`badge badge-status-${dup.status || 'open'}`} style={{ fontSize: '0.72rem' }}>
                    {dup.status}
                  </span>
                  <span className="badge" style={{ fontSize: '0.72rem', background: 'var(--bg-dark-accent)', color: 'var(--text-muted)' }}>
                    {dup.similarity_score}% Similar
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="form-group">
        <label>Summary Description *</label>
        <textarea
          value={form.description}
          onChange={(e) => set('description', e.target.value)}
          onBlur={() => {
            autoPredictSeverity();
            handleClassify();
            handleDetectDuplicates();
          }}
          placeholder="Brief summary of the issue..."
          required
          rows={3}
        />
      </div>

      {/* Classification Details Row (Category, Module, Defect Type) */}
      <div className="form-row">
        <div className="form-group">
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <Tag size={13} /> Defect Category
          </label>
          <input
            list="category-options"
            value={form.category || ''}
            onChange={(e) => set('category', e.target.value)}
            placeholder="e.g. Payment, Auth, UI/UX"
          />
          <datalist id="category-options">
            <option value="Payment" />
            <option value="Authentication & Security" />
            <option value="UI / UX" />
            <option value="Database & Storage" />
            <option value="Performance" />
            <option value="API & Backend" />
            <option value="Notifications & Messaging" />
            <option value="Reporting & Analytics" />
          </datalist>
        </div>

        <div className="form-group">
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <Layers size={13} /> Module / Component
          </label>
          <input
            list="module-options"
            value={form.module || ''}
            onChange={(e) => set('module', e.target.value)}
            placeholder="e.g. Checkout / Payment Gateway"
          />
          <datalist id="module-options">
            <option value="Checkout / Payment Gateway" />
            <option value="Auth / User Session" />
            <option value="Navigation & Layout" />
            <option value="User Profile" />
            <option value="Sprint Board & Kanban" />
            <option value="Notification Service" />
            <option value="Analytics Engine" />
          </datalist>
        </div>

        <div className="form-group">
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            <ShieldAlert size={13} /> Defect Type
          </label>
          <select
            value={form.defect_type || ''}
            onChange={(e) => set('defect_type', e.target.value)}
          >
            <option value="">-- Select Defect Type --</option>
            <option value="Functional Defect">Functional Defect</option>
            <option value="Crash / Fatal Error">Crash / Fatal Error</option>
            <option value="UI / Visual Glitch">UI / Visual Glitch</option>
            <option value="Security / Access Defect">Security / Access Defect</option>
            <option value="Performance Bottleneck">Performance Bottleneck</option>
            <option value="Data Integrity Issue">Data Integrity Issue</option>
            <option value="Compatibility Issue">Compatibility Issue</option>
          </select>
        </div>
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
                <Sparkles size={11} color="var(--accent)" /> AI Suggested
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
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.35rem', lineHeight: '1.4' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.3rem', color: 'var(--text)' }}>
                <Info size={13} style={{ flexShrink: 0, marginTop: '2px', color: 'var(--accent)' }} />
                <span>{severityRationale}</span>
              </div>
              <div style={{ fontSize: '0.71rem', color: 'var(--text-dim)', marginTop: '0.2rem', fontStyle: 'italic' }}>
                * AI suggestion provided. The final decision remains with the authorized user.
              </div>
            </div>
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
