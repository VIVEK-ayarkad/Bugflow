import { useEffect, useState } from 'react';
import { Trash2, X, Paperclip, FileText, Download } from 'lucide-react';
import {
  addComment,
  assignIssue,
  deleteAttachment,
  deleteComment,
  deleteIssue,
  editComment,
  getAttachments,
  getComments,
  getUsers,
  updateIssueStatus,
  uploadAttachment,
} from '../api';
import { useAuth } from '../AuthContext';

const WORKFLOW_STEPS = [
  { id: 'open', label: 'Open' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'in_review', label: 'In Review' },
  { id: 'resolved', label: 'Resolved' },
  { id: 'closed', label: 'Closed' },
];

export default function BugDetailModal({ issue, onClose, onRefresh }) {
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

  useEffect(() => {
    setCurrentIssue(issue);
    if (issue) {
      loadComments(issue.id);
      loadAttachments(issue.id);
      loadDevelopers();
    }
  }, [issue]);

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

  if (!currentIssue) return null;

  const currentStepIdx = WORKFLOW_STEPS.findIndex((s) => s.id === currentIssue.status);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
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

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
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

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span className="meta-label">Assigned Developer:</span>
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
            className={`tab-btn ${activeTab === 'attachments' ? 'active' : ''}`}
            onClick={() => setActiveTab('attachments')}
          >
            File Attachments ({attachments.length})
          </button>
        </div>

        {/* Tab Content */}
        <div className="modal-tab-body">
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
                        <a
                          href={`/api/attachments/${att.id}/download`}
                          target="_blank"
                          rel="noreferrer"
                          className="btn-link-sm"
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}
                        >
                          <Download size={12} /> Download
                        </a>
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
        </div>
      </div>
    </div>
  );
}
