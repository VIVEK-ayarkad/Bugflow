import { useEffect, useState } from 'react';
import {
  Trash2,
  X,
  Paperclip,
  FileText,
  Download,
  FileDown,
  Sparkles,
  Lightbulb,
  CheckSquare,
  Square,
  Copy,
  Check,
  ArrowRight,
  Pencil,
  BookOpen,
  MessageSquare,
  History,
  Bot,
  Zap,
} from 'lucide-react';
import BlastRadiusVisualizer from './BlastRadiusVisualizer';
import {
  addComment,
  assignIssue,
  deleteAttachment,
  deleteComment,
  deleteIssue,
  downloadAttachmentFile,
  downloadIssuePdf,
  editComment,
  getAttachments,
  getComments,
  getResolutionAssistance,
  getUsers,
  updateIssue,
  updateIssueStatus,
  uploadAttachment,
} from '../api';
import { useAuth } from '../AuthContext';
import IssueForm from './IssueForm';

const WORKFLOW_STEPS = [
  { id: 'open', label: 'Open' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'in_review', label: 'In Review' },
  { id: 'resolved', label: 'Resolved' },
  { id: 'closed', label: 'Closed' },
];

export default function BugDetailModal({ issue, onClose, onRefresh, onOpenAIChat = null }) {
  const { user, hasRole } = useAuth();
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'comments' | 'attachments'
  const [currentIssue, setCurrentIssue] = useState(issue);
  const [comments, setComments] = useState([]);
  const [attachments, setAttachments] = useState([]);
  const [developers, setDevelopers] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [uploading, setUploading] = useState(false);
  const [loadingComments, setLoadingComments] = useState(false);
  const [editingCommentId, setEditingCommentId] = useState(null);
  const [editingCommentText, setEditingCommentText] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingAttId, setDownloadingAttId] = useState(null);
  const [resolutionAssistance, setResolutionAssistance] = useState(null);
  const [loadingAssistance, setLoadingAssistance] = useState(false);
  const [checkedAreas, setCheckedAreas] = useState({});
  const [copiedFix, setCopiedFix] = useState(false);
  const [copiedHistIdx, setCopiedHistIdx] = useState(null);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    setCurrentIssue(issue);
    if (issue) {
      loadComments(issue.id);
      loadAttachments(issue.id);
      loadDevelopers();
      loadResolutionAssistance(issue.id);
      setIsEditing(false);
    }
  }, [issue]);

  async function loadResolutionAssistance(issueId) {
    setLoadingAssistance(true);
    try {
      const data = await getResolutionAssistance(issueId);
      setResolutionAssistance(data);
    } catch {
      // ignore
    } finally {
      setLoadingAssistance(false);
    }
  }

  async function handleEditSubmit(payload) {
    try {
      const updated = await updateIssue(currentIssue.id, payload);
      setCurrentIssue(updated);
      setIsEditing(false);
      onRefresh();
      loadResolutionAssistance(updated.id);
    } catch (err) {
      alert(`Failed to update bug: ${err.message}`);
    }
  }

  async function loadDevelopers() {
    try {
      const data = await getUsers();
      setDevelopers(data);
    } catch {
      // ignore
    }
  }

  async function loadComments(issueId) {
    setLoadingComments(true);
    try {
      const data = await getComments(issueId);
      setComments(data);
    } catch {
      // ignore
    } finally {
      setLoadingComments(false);
    }
  }

  async function loadAttachments(issueId) {
    try {
      const data = await getAttachments(issueId);
      setAttachments(data);
    } catch {
      // ignore
    }
  }

  async function handleStatusChange(newStatus) {
    try {
      const updated = await updateIssueStatus(currentIssue.id, newStatus);
      setCurrentIssue(updated);
      onRefresh();
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleAssignChange(devId) {
    try {
      const updated = await assignIssue(currentIssue.id, devId ? parseInt(devId) : null);
      setCurrentIssue(updated);
      onRefresh();
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleDeleteBug() {
    if (!window.confirm(`Are you sure you want to delete Bug #${currentIssue.id} (${currentIssue.title})?`)) return;
    setDeleting(true);
    try {
      await deleteIssue(currentIssue.id);
      onClose();
      onRefresh();
    } catch (err) {
      alert(err.message);
    } finally {
      setDeleting(false);
    }
  }

  async function handleAddComment(e) {
    e.preventDefault();
    if (!newComment.trim()) return;
    try {
      const added = await addComment(currentIssue.id, newComment);
      setComments((prev) => [...prev, added]);
      setNewComment('');
      onRefresh();
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleSaveEditComment(commentId) {
    if (!editingCommentText.trim()) return;
    try {
      const updated = await editComment(commentId, editingCommentText);
      setComments((prev) => prev.map((c) => (c.id === commentId ? updated : c)));
      setEditingCommentId(null);
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleDeleteComment(commentId) {
    if (!window.confirm('Delete this comment?')) return;
    try {
      await deleteComment(commentId);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
      onRefresh();
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    try {
      const att = await uploadAttachment(currentIssue.id, file);
      setAttachments((prev) => [att, ...prev]);
      onRefresh();
    } catch (err) {
      alert(err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleDeleteAttachment(attId) {
    if (!window.confirm('Delete attachment?')) return;
    try {
      await deleteAttachment(attId);
      setAttachments((prev) => prev.filter((a) => a.id !== attId));
      onRefresh();
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleDownloadPdf() {
    if (!currentIssue) return;
    setDownloadingPdf(true);
    try {
      await downloadIssuePdf(currentIssue.id);
    } catch (err) {
      alert(`Failed to download PDF: ${err.message}`);
    } finally {
      setDownloadingPdf(false);
    }
  }

  async function handleDownloadAttachment(att) {
    if (!att) return;
    setDownloadingAttId(att.id);
    try {
      await downloadAttachmentFile(att.id, att.filename);
    } catch (err) {
      alert(`Failed to download attachment: ${err.message}`);
    } finally {
      setDownloadingAttId(null);
    }
  }

  function toggleCheckArea(idx) {
    setCheckedAreas((prev) => ({ ...prev, [idx]: !prev[idx] }));
  }

  function handleCopyFix() {
    if (!resolutionAssistance?.possible_resolution) return;
    navigator.clipboard.writeText(resolutionAssistance.possible_resolution);
    setCopiedFix(true);
    setTimeout(() => setCopiedFix(false), 2500);
  }

  function handleCopyHistoricalFix(fixText, idx) {
    if (!fixText) return;
    navigator.clipboard.writeText(fixText);
    setCopiedHistIdx(idx);
    setTimeout(() => setCopiedHistIdx(null), 2500);
  }

  async function handleApplyResolutionComment() {
    if (!resolutionAssistance?.possible_resolution) return;
    const text = `💡 **Applied Resolution:**\n${resolutionAssistance.possible_resolution}`;
    try {
      const c = await addComment(currentIssue.id, text);
      setComments((prev) => [...prev, c]);
      setActiveTab('comments');
      alert('Resolution note posted to discussion comments!');
    } catch (err) {
      alert(err.message);
    }
  }

  if (!currentIssue) return null;

  const currentStepIdx = WORKFLOW_STEPS.findIndex((s) => s.id === currentIssue.status);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
              <span className="bug-id-tag">#BUG-{currentIssue.id}</span>
              <span className={`badge badge-${currentIssue.severity}`}>
                {currentIssue.severity} severity
              </span>
              <span className={`badge badge-${currentIssue.priority}`}>{currentIssue.priority} priority</span>
            </div>
            <h2 style={{ margin: '0.2rem 0', fontSize: '1.3rem' }}>{currentIssue.title}</h2>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            {onOpenAIChat && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={() =>
                  onOpenAIChat({
                    issue_id: currentIssue.id,
                    issue_title: currentIssue.title,
                    issue_description: currentIssue.description,
                    category: currentIssue.category,
                    module: currentIssue.module,
                    severity: currentIssue.severity,
                    status: currentIssue.status,
                  })
                }
                title="Ask AI Mentor how to diagnose, reproduce, or resolve this bug"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', background: 'var(--accent-light)', borderColor: 'var(--accent)', color: 'var(--accent)' }}
              >
                <Bot size={14} /> Ask AI Mentor
              </button>
            )}
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setIsEditing(!isEditing)}
              title={isEditing ? "Cancel Editing" : "Edit Defect Details"}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', borderColor: isEditing ? 'var(--accent)' : 'var(--border)' }}
            >
              <Pencil size={14} />
              {isEditing ? 'Cancel Edit' : 'Edit Bug'}
            </button>
            <button
              className="btn btn-secondary btn-sm"
              onClick={handleDownloadPdf}
              disabled={downloadingPdf}
              title="Download Defect Report as PDF"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', borderColor: 'var(--accent)', color: 'var(--accent)' }}
            >
              <FileDown size={14} />
              {downloadingPdf ? 'Generating PDF...' : 'Download PDF Report'}
            </button>
            <button
              className="btn btn-secondary btn-sm danger"
              onClick={handleDeleteBug}
              disabled={deleting}
              title="Delete this bug report"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
            >
              <Trash2 size={14} />
              {deleting ? 'Deleting...' : 'Delete Bug'}
            </button>
            <button className="btn-icon" onClick={onClose} title="Close Modal">
              <X size={18} />
            </button>
          </div>
        </div>

        {isEditing ? (
          <div style={{ marginTop: '1.2rem', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '1.1rem' }}>
                <Pencil size={18} /> Edit Defect #{currentIssue.id}
              </h3>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setIsEditing(false)}
              >
                Back to Details
              </button>
            </div>
            <IssueForm
              initial={currentIssue}
              projectId={currentIssue.project_id}
              onSubmit={handleEditSubmit}
              onCancel={() => setIsEditing(false)}
              submitLabel="Save Changes"
            />
          </div>
        ) : (
          <>
            {/* Workflow Stepper */}
            <div className="workflow-stepper">
              {WORKFLOW_STEPS.map((step, idx) => {
                const isActive = step.id === currentIssue.status;
                const isPassed = idx <= currentStepIdx;

                return (
                  <div
                    key={step.id}
                    className={`stepper-step ${isActive ? 'active' : isPassed ? 'passed' : ''}`}
                    onClick={() => handleStatusChange(step.id)}
                  >
                    <div className="step-number">{idx + 1}</div>
                    <span className="step-label">{step.label}</span>
                  </div>
                );
              })}
            </div>

        {/* Metadata Strip */}
        <div className="meta-strip">
          <div>
            <span className="meta-label">Reporter:</span>{' '}
            <strong>{currentIssue.reporter?.username || 'System'}</strong>
          </div>

          {currentIssue.category && (
            <div>
              <span className="meta-label">Category:</span>{' '}
              <span className="badge" style={{ background: 'var(--accent-light)', color: 'var(--accent)', borderColor: 'var(--border)' }}>
                {currentIssue.category}
              </span>
            </div>
          )}

          {currentIssue.module && (
            <div>
              <span className="meta-label">Module:</span>{' '}
              <strong>{currentIssue.module}</strong>
            </div>
          )}

          {currentIssue.defect_type && (
            <div>
              <span className="meta-label">Type:</span>{' '}
              <span className="badge" style={{ background: 'var(--bg-dark-accent)', color: 'var(--text)' }}>
                {currentIssue.defect_type}
              </span>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span className="meta-label">Assigned:</span>
            <select
              value={currentIssue.assigned_developer_id || ''}
              onChange={(e) => handleAssignChange(e.target.value)}
              className="select-sm"
            >
              <option value="">-- Unassigned --</option>
              {developers.map((dev) => (
                <option key={dev.id} value={dev.id}>
                  {dev.username}
                </option>
              ))}
            </select>
          </div>

          <div>
            <span className="meta-label">Created:</span>{' '}
            {new Date(currentIssue.created_at).toLocaleDateString()}
          </div>
        </div>

        {/* Tabs */}
        <div className="modal-tabs">
          <button
            className={`tab-btn ${activeTab === 'resolution' ? 'active' : ''}`}
            onClick={() => setActiveTab('resolution')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              color: activeTab === 'resolution' ? 'var(--accent)' : 'inherit',
              fontWeight: '700'
            }}
          >
            <Sparkles size={14} color="#8b5cf6" /> Resolution Assistance
          </button>
          <button
            className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            Overview & Details
          </button>
          <button
            className={`tab-btn ${activeTab === 'comments' ? 'active' : ''}`}
            onClick={() => setActiveTab('comments')}
          >
            Discussion Comments ({comments.length})
          </button>
          <button
            className={`tab-btn ${activeTab === 'blast_radius' ? 'active' : ''}`}
            onClick={() => setActiveTab('blast_radius')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.4rem',
              color: activeTab === 'blast_radius' ? '#f59e0b' : 'inherit',
              fontWeight: '700'
            }}
          >
            <Zap size={14} color="#f59e0b" /> ⚡ Blast Radius & Cascade
          </button>
          <button
            className={`tab-btn ${activeTab === 'attachments' ? 'active' : ''}`}
            onClick={() => setActiveTab('attachments')}
          >
            File Attachments ({attachments.length})
          </button>
        </div>

        {/* Tab Content */}
        <div className="modal-tab-body">
          {activeTab === 'resolution' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
              {loadingAssistance ? (
                <div style={{ textAlign: 'center', padding: '2.5rem 1rem', color: 'var(--text-muted)' }}>
                  <Sparkles size={26} style={{ color: 'var(--accent)', animation: 'spin 2s linear infinite' }} />
                  <p style={{ marginTop: '0.6rem', fontSize: '0.9rem' }}>Analyzing defect patterns and generating resolution intelligence...</p>
                </div>
              ) : resolutionAssistance ? (
                <>
                  {/* Header Banner */}
                  <div style={{ background: 'linear-gradient(135deg, rgba(79, 70, 229, 0.08), rgba(124, 58, 237, 0.12))', border: '1px solid rgba(124, 58, 237, 0.25)', borderRadius: 'var(--radius-md)', padding: '1rem 1.25rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.4rem' }}>
                      <h3 style={{ margin: 0, display: 'inline-flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text)', fontSize: '1.05rem' }}>
                        <Lightbulb size={18} color="#a855f7" /> Resolution Intelligence Copilot
                      </h3>
                      <span className="badge" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', borderColor: '#a855f7', fontSize: '0.74rem' }}>
                        ✨ Signature Feature
                      </span>
                    </div>
                    <p style={{ margin: '0 0 0.6rem 0', fontSize: '0.86rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                      Diagnostic investigation checklist, similar defect resolutions, and recommended code fix for <strong>"{currentIssue.title}"</strong>.
                    </p>
                    {resolutionAssistance.context_signals_used?.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontWeight: '600' }}>Context Analyzed:</span>
                        {resolutionAssistance.context_signals_used.map((signal, sIdx) => (
                          <span
                            key={sIdx}
                            className="badge"
                            style={{
                              fontSize: '0.7rem',
                              background: 'rgba(79, 70, 229, 0.15)',
                              color: '#a5b4fc',
                              borderColor: 'rgba(99, 102, 241, 0.3)',
                              textTransform: 'capitalize'
                            }}
                          >
                            ✓ {signal.replace('_', ' ')}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Severity Mitigation Strategy */}
                  {resolutionAssistance.severity_mitigation && (
                    <div style={{
                      padding: '0.8rem 1rem',
                      borderRadius: 'var(--radius-md)',
                      background: currentIssue.severity === 'critical' ? 'rgba(239, 68, 68, 0.08)' : currentIssue.severity === 'high' ? 'rgba(245, 158, 11, 0.08)' : 'rgba(59, 130, 246, 0.08)',
                      border: `1px solid ${currentIssue.severity === 'critical' ? 'rgba(239, 68, 68, 0.3)' : currentIssue.severity === 'high' ? 'rgba(245, 158, 11, 0.3)' : 'rgba(59, 130, 246, 0.25)'}`,
                      fontSize: '0.86rem',
                      lineHeight: '1.55',
                      color: 'var(--text)'
                    }}>
                      {resolutionAssistance.severity_mitigation}
                    </div>
                  )}

                  {/* Section 1: Root Cause Investigation Suggestions */}
                  <div className="detail-section">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.4rem', margin: '0 0 0.4rem 0' }}>
                      <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent)', margin: 0, fontSize: '0.98rem' }}>
                        🔍 Root Cause Investigation Suggestions:
                      </h4>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                        {Object.values(checkedAreas).filter(Boolean).length} / {resolutionAssistance.investigation_areas?.length || 0} completed
                      </span>
                    </div>

                    {/* Non-guaranteed Advisory Disclaimer */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.45rem',
                      padding: '0.45rem 0.75rem',
                      borderRadius: 'var(--radius-sm)',
                      background: 'rgba(59, 130, 246, 0.06)',
                      border: '1px solid rgba(59, 130, 246, 0.2)',
                      marginBottom: '0.65rem',
                      fontSize: '0.78rem',
                      color: 'var(--text-muted)'
                    }}>
                      <Lightbulb size={14} color="#38bdf8" style={{ flexShrink: 0 }} />
                      <span>{resolutionAssistance.investigation_disclaimer || "These diagnostic suggestions guide developer triage and investigation, but are not guaranteed root causes."}</span>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                      {resolutionAssistance.investigation_areas?.map((area, idx) => {
                        const isChecked = !!checkedAreas[idx];
                        return (
                          <div
                            key={idx}
                            onClick={() => toggleCheckArea(idx)}
                            style={{
                              display: 'flex',
                              alignItems: 'flex-start',
                              gap: '0.6rem',
                              padding: '0.6rem 0.8rem',
                              borderRadius: 'var(--radius-sm)',
                              background: isChecked ? 'rgba(5, 150, 105, 0.08)' : 'var(--bg-dark-accent)',
                              border: `1px solid ${isChecked ? '#059669' : 'var(--border)'}`,
                              cursor: 'pointer',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            {isChecked ? (
                              <CheckSquare size={16} color="#059669" style={{ marginTop: '0.15rem', flexShrink: 0 }} />
                            ) : (
                              <Square size={16} color="var(--text-dim)" style={{ marginTop: '0.15rem', flexShrink: 0 }} />
                            )}
                            <span style={{ fontSize: '0.88rem', color: isChecked ? 'var(--text-muted)' : 'var(--text)', textDecoration: isChecked ? 'line-through' : 'none' }}>
                              {area}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Section 2: Similar Defects */}
                  {resolutionAssistance.similar_defects?.length > 0 && (
                    <div className="detail-section">
                      <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent)', margin: '0 0 0.6rem 0' }}>
                        ⚠️ Similar Defects:
                      </h4>
                      <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                        {resolutionAssistance.similar_defects.map((sd) => (
                          <div
                            key={sd.id}
                            style={{
                              padding: '0.6rem 0.85rem',
                              borderRadius: 'var(--radius-sm)',
                              background: 'var(--bg-dark-accent)',
                              border: '1px solid var(--border)',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.6rem',
                              fontSize: '0.84rem'
                            }}
                          >
                            <span className="bug-id-tag">#{sd.key}</span>
                            <span style={{ fontWeight: '600', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {sd.title}
                            </span>
                            <span className={`badge badge-${sd.status}`}>
                              {sd.status}
                            </span>
                            <span className="badge" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', fontSize: '0.7rem' }}>
                              {sd.similarity_score}% Match
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Section 3: Historical Resolution Knowledge Base */}
                  {resolutionAssistance.historical_resolutions?.length > 0 ? (
                    <div className="detail-section">
                      <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#10b981', margin: '0 0 0.75rem 0' }}>
                        <BookOpen size={16} /> Historical Resolution Knowledge Base ({resolutionAssistance.historical_resolutions.length} Resolved Similar Defects):
                      </h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem' }}>
                        {resolutionAssistance.historical_resolutions.map((hist, hIdx) => (
                          <div
                            key={hist.defect_id || hIdx}
                            style={{
                              background: 'var(--bg-dark-accent)',
                              border: '1px solid rgba(16, 185, 129, 0.25)',
                              borderRadius: 'var(--radius-md)',
                              padding: '1rem 1.2rem',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '0.65rem'
                            }}
                          >
                            {/* Defect Header */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                <span className="bug-id-tag">#{hist.defect_key}</span>
                                <strong style={{ color: 'var(--text)', fontSize: '0.95rem' }}>{hist.title}</strong>
                                <span className="badge badge-resolved">{hist.status}</span>
                                <span className={`badge badge-severity badge-${hist.severity.toLowerCase()}`}>{hist.severity}</span>
                              </div>
                              <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399', fontSize: '0.75rem', fontWeight: '600' }}>
                                {hist.similarity_score}% Similar
                              </span>
                            </div>

                            {/* Previous Root Cause */}
                            <div style={{
                              background: 'rgba(245, 158, 11, 0.08)',
                              border: '1px solid rgba(245, 158, 11, 0.25)',
                              borderRadius: 'var(--radius-sm)',
                              padding: '0.6rem 0.8rem',
                              fontSize: '0.86rem'
                            }}>
                              <strong style={{ color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '0.3rem', marginBottom: '0.2rem' }}>
                                🔍 Previous Root Cause:
                              </strong>
                              <span style={{ color: 'var(--text)', lineHeight: '1.5' }}>{hist.previous_root_cause}</span>
                            </div>

                            {/* Previous Resolution */}
                            <div style={{
                              background: 'rgba(16, 185, 129, 0.08)',
                              border: '1px solid rgba(16, 185, 129, 0.25)',
                              borderRadius: 'var(--radius-sm)',
                              padding: '0.6rem 0.8rem',
                              fontSize: '0.86rem'
                            }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
                                <strong style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                  ✅ Previous Resolution Applied:
                                </strong>
                                <button
                                  type="button"
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => handleCopyHistoricalFix(hist.previous_resolution, hIdx)}
                                  style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                                >
                                  {copiedHistIdx === hIdx ? <Check size={12} color="#059669" /> : <Copy size={12} />}
                                  {copiedHistIdx === hIdx ? 'Copied' : 'Copy'}
                                </button>
                              </div>
                              <span style={{ color: 'var(--text)', lineHeight: '1.5' }}>{hist.previous_resolution}</span>
                            </div>

                            {/* Relevant Developer Comments */}
                            {hist.relevant_developer_comments?.length > 0 && (
                              <div style={{ marginTop: '0.2rem' }}>
                                <span style={{ fontSize: '0.78rem', fontWeight: '600', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.3rem', marginBottom: '0.35rem' }}>
                                  <MessageSquare size={13} /> Relevant Developer Investigation Comments ({hist.relevant_developer_comments.length}):
                                </span>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                                  {hist.relevant_developer_comments.slice(0, 3).map((comm, cIdx) => (
                                    <div
                                      key={cIdx}
                                      style={{
                                        background: 'var(--bg-dark)',
                                        border: '1px solid var(--border)',
                                        borderRadius: 'var(--radius-sm)',
                                        padding: '0.5rem 0.75rem',
                                        fontSize: '0.82rem'
                                      }}
                                    >
                                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                          <strong style={{ color: 'var(--accent)' }}>@{comm.author}</strong>
                                          {comm.role && <span className="badge" style={{ fontSize: '0.65rem' }}>{comm.role}</span>}
                                        </div>
                                        {comm.created_at && <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>{comm.created_at}</span>}
                                      </div>
                                      <p style={{ margin: 0, color: 'var(--text-muted)', lineHeight: '1.45' }}>{comm.content}</p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : resolutionAssistance.previous_resolution ? (
                    <div style={{ background: 'rgba(5, 150, 105, 0.08)', border: '1px solid rgba(5, 150, 105, 0.25)', borderRadius: 'var(--radius-md)', padding: '0.9rem 1.1rem' }}>
                      <h4 style={{ margin: '0 0 0.4rem 0', color: '#059669', fontSize: '0.92rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <BookOpen size={16} /> Previous Resolution Precedent:
                      </h4>
                      <p style={{ margin: 0, fontSize: '0.88rem', color: 'var(--text)', lineHeight: '1.6' }}>
                        {resolutionAssistance.previous_resolution}
                      </p>
                    </div>
                  ) : null}

                  {/* Section 4: Possible Resolution */}
                  <div style={{ background: 'linear-gradient(135deg, rgba(79, 70, 229, 0.08), rgba(2, 132, 199, 0.08))', border: '1px solid rgba(79, 70, 229, 0.3)', borderRadius: 'var(--radius-md)', padding: '1rem 1.25rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.6rem' }}>
                      <h4 style={{ margin: 0, color: 'var(--accent)', fontSize: '0.96rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        🚀 Possible Resolution:
                      </h4>
                      <div style={{ display: 'flex', gap: '0.4rem' }}>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={handleCopyFix}
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                        >
                          {copiedFix ? <Check size={13} color="#059669" /> : <Copy size={13} />}
                          {copiedFix ? 'Copied!' : 'Copy Fix'}
                        </button>
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={handleApplyResolutionComment}
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                        >
                          <ArrowRight size={13} /> Post to Comments
                        </button>
                      </div>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text)', lineHeight: '1.65', fontWeight: '500' }}>
                      {resolutionAssistance.possible_resolution}
                    </p>
                  </div>
                </>
              ) : (
                <p className="text-muted">No resolution assistance available for this defect.</p>
              )}
            </div>
          )}

          {activeTab === 'overview' && (
            <div>
              <div className="detail-section">
                <h4>Description</h4>
                <div className="markdown-content">{currentIssue.description}</div>
              </div>

              {currentIssue.steps_to_reproduce && (
                <div className="detail-section">
                  <h4>Steps to Reproduce</h4>
                  <pre className="code-block">{currentIssue.steps_to_reproduce}</pre>
                </div>
              )}

              {currentIssue.expected_behavior && (
                <div className="detail-section">
                  <h4>Expected Result</h4>
                  <div className="markdown-content">{currentIssue.expected_behavior}</div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'comments' && (
            <div>
              <div className="comments-list">
                {comments.map((c) => (
                  <div key={c.id} className="comment-card">
                    <div className="comment-header">
                      <strong>{c.user?.username || 'User'}</strong>
                      <span className="comment-date">{new Date(c.created_at).toLocaleString()}</span>
                    </div>

                    {editingCommentId === c.id ? (
                      <div style={{ marginTop: '0.5rem' }}>
                        <textarea
                          value={editingCommentText}
                          onChange={(e) => setEditingCommentText(e.target.value)}
                          rows={2}
                        />
                        <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.4rem' }}>
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => handleSaveEditComment(c.id)}
                          >
                            Save
                          </button>
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => setEditingCommentId(null)}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="comment-body">{c.content}</div>
                        {(user?.id === c.user_id || hasRole('admin')) && (
                          <div className="comment-actions">
                            <button
                              className="btn-link-sm"
                              onClick={() => {
                                setEditingCommentId(c.id);
                                setEditingCommentText(c.content);
                              }}
                            >
                              Edit
                            </button>
                            <button
                              className="btn-link-sm danger"
                              onClick={() => handleDeleteComment(c.id)}
                            >
                              Delete
                            </button>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>

              <form onSubmit={handleAddComment} style={{ marginTop: '1rem' }}>
                <textarea
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Write a comment..."
                  rows={2}
                  required
                />
                <button type="submit" className="btn btn-primary btn-sm" style={{ marginTop: '0.5rem' }}>
                  Post Comment
                </button>
              </form>
            </div>
          )}

          {activeTab === 'attachments' && (
            <div>
              <div style={{ marginBottom: '1rem' }}>
                <label className="btn btn-secondary btn-sm" style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                  <Paperclip size={14} />
                  {uploading ? 'Uploading...' : 'Upload Screenshot / File'}
                  <input type="file" onChange={handleFileUpload} style={{ display: 'none' }} disabled={uploading} />
                </label>
              </div>

              <div className="attachments-grid">
                {attachments.length === 0 ? (
                  <p className="text-muted">No attachments uploaded yet.</p>
                ) : (
                  attachments.map((att) => (
                    <div key={att.id} className="attachment-card">
                      <div className="att-info">
                        <span className="att-name" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                          <FileText size={14} /> {att.filename}
                        </span>
                        <span className="att-size">{(att.file_size / 1024).toFixed(1)} KB</span>
                      </div>
                      <div className="att-actions">
                        <button
                          type="button"
                          onClick={() => handleDownloadAttachment(att)}
                          disabled={downloadingAttId === att.id}
                          className="btn-link-sm"
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.2rem',
                            cursor: downloadingAttId === att.id ? 'wait' : 'pointer',
                            background: 'none',
                            border: 'none',
                            padding: 0,
                            font: 'inherit',
                          }}
                        >
                          <Download size={12} /> {downloadingAttId === att.id ? 'Downloading...' : 'Download'}
                        </button>
                        {(user?.id === att.user_id || hasRole('admin')) && (
                          <button
                            className="btn-link-sm danger"
                            onClick={() => handleDeleteAttachment(att.id)}
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {activeTab === 'blast_radius' && (
            <div style={{ marginTop: '0.5rem' }}>
              <BlastRadiusVisualizer
                projectId={currentIssue.project_id}
                initialFocusedIssueId={currentIssue.id}
                issues={[currentIssue]}
                embedded={true}
              />
            </div>
          )}
        </div>
        </>
        )}
      </div>
    </div>
  );
}
