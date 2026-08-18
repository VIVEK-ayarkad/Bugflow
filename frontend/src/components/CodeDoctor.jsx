import { useEffect, useState } from 'react';
import { Bot, Sparkles, AlertTriangle, Lightbulb, BookmarkPlus, Code, CheckCircle, Copy } from 'lucide-react';
import { aiFixCode, createIssue } from '../api';

const SAMPLES = [
  {
    label: 'Python Syntax / Unclosed Quote',
    lang: 'python',
    code: `print("hell)`,
    err: `SyntaxError: unterminated string literal (detected at line 1)`,
  },
  {
    label: 'JS Undefined .map()',
    lang: 'javascript',
    code: `const items = undefined;\nconst list = items.map(item => item.name);\nconsole.log(list);`,
    err: `TypeError: Cannot read properties of undefined (reading 'map')`,
  },
  {
    label: 'Python KeyError',
    lang: 'python',
    code: `user_data = {"username": "alex", "role": "admin"}\nprint("Age:", user_data["age"])`,
    err: `KeyError: 'age'`,
  },
  {
    label: 'SQL Unsafe Null Query',
    lang: 'sql',
    code: `SELECT user_id, email, last_login_date FROM users WHERE active = 1 AND deleted = NULL;`,
    err: `Query returns NULL on missing last_login_date column for new accounts`,
  },
  {
    label: 'Java NullPointerException',
    lang: 'java',
    code: `String username = user.getProfile().getUsername();\nSystem.out.println(username.toUpperCase());`,
    err: `java.lang.NullPointerException: Cannot invoke getProfile() because user is null`,
  },
];

export default function CodeDoctor({ projects = [], onIssueCreated }) {
  const [language, setLanguage] = useState('javascript');
  const [code, setCode] = useState('');
  const [sampleErr, setSampleErr] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [copyToast, setCopyToast] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState(projects[0]?.id || '');
  const [loggingIssue, setLoggingIssue] = useState(false);
  const [issueCreatedNotice, setIssueCreatedNotice] = useState('');

  useEffect(() => {
    if (projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  const handleFixCode = async (e) => {
    if (e) e.preventDefault();
    if (!code.trim()) return;

    setLoading(true);
    setError('');
    setResult(null);
    setIssueCreatedNotice('');

    try {
      const res = await aiFixCode({
        code,
        error_log: sampleErr,
        language,
      });
      setResult(res);
    } catch (err) {
      setError(err.message || 'Failed to analyze code snippet');
    } finally {
      setLoading(false);
    }
  };

  const handleApplySample = (sample) => {
    setLanguage(sample.lang);
    setCode(sample.code);
    setSampleErr(sample.err || '');
    setResult(null);
    setError('');
  };

  const handleCopyCode = () => {
    if (!result?.corrected_code) return;
    navigator.clipboard.writeText(result.corrected_code);
    setCopyToast('Copied Corrected Code to Clipboard!');
    setTimeout(() => setCopyToast(''), 2500);
  };

  const handleCreateIssueFromFix = async () => {
    if (!selectedProjectId || !result) return;
    setLoggingIssue(true);
    try {
      const newIssue = await createIssue(selectedProjectId, {
        title: `Fix: ${result.root_cause.slice(0, 70)}`,
        description: `### AI Code Doctor Analysis\n\n**User Mistake:**\n${result.user_mistake || 'N/A'}\n\n**Root Cause:**\n${result.root_cause}\n\n**Explanation:**\n${result.explanation}\n\n### Original Code:\n\`\`\`${language}\n${code}\n\`\`\`\n\n### Corrected Code:\n\`\`\`${language}\n${result.corrected_code}\n\`\`\``,
        status: 'open',
        priority: 'high',
      });
      setIssueCreatedNotice(`Created Issue #${newIssue.id} in project successfully!`);
      if (onIssueCreated) onIssueCreated(newIssue);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoggingIssue(false);
    }
  };

  return (
    <div className="card">
      <div className="page-header" style={{ marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Bot size={26} color="var(--accent)" />
            AI Code Doctor & Instant Debugger
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.2rem' }}>
            Paste any broken snippet or error trace, and AI will diagnose root causes and generate production-ready fixes.
          </p>
        </div>
      </div>

      {/* Preset Sample Chips */}
      <div style={{ marginBottom: '1.25rem' }}>
        <div style={{ fontSize: '0.78rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim)', marginBottom: '0.5rem' }}>
          Try Instant Presets:
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {SAMPLES.map((sample, idx) => (
            <button
              key={idx}
              type="button"
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '0.78rem' }}
              onClick={() => handleApplySample(sample)}
            >
              + {sample.label}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleFixCode}>
        <div className="form-row" style={{ marginBottom: '1rem' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Programming Language</label>
            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
              <option value="javascript">JavaScript / React</option>
              <option value="python">Python</option>
              <option value="typescript">TypeScript</option>
              <option value="sql">SQL</option>
              <option value="html">HTML / CSS</option>
              <option value="java">Java / C++</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Code size={16} />
            Broken Code Snippet
          </label>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Paste your broken function, SQL query, or component code here..."
            rows={6}
            style={{ fontFamily: 'var(--mono)', fontSize: '0.85rem' }}
            required
          />
        </div>

        {error && (
          <div className="error" style={{ marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        <button type="submit" className="btn btn-ai" style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }} disabled={loading || !code.trim()}>
          {loading ? (
            <>
              <div className="spinner" style={{ width: '18px', height: '18px', borderWidth: '2px' }} />
              Diagnosing & Fixing Code…
            </>
          ) : (
            <>
              <Sparkles size={16} />
              Fix Code with AI Doctor
            </>
          )}
        </button>
      </form>

      {/* AI Doctor Result Box */}
      {result && (
        <div style={{ marginTop: '1.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border)' }}>
          <div className="copilot-diagnosis-box" style={{ marginTop: 0 }}>
            {/* Header */}
            <div className="copilot-header">
              <div className="copilot-title" style={{ color: result.is_correct ? 'var(--success)' : 'var(--accent)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <CheckCircle size={18} color={result.is_correct ? 'var(--success)' : 'var(--accent)'} />
                {result.is_correct ? 'Code is Valid & Correct' : 'Bug Diagnosed & Fix Ready'}
              </div>
              <span className="layer-tag" style={result.is_correct ? { background: 'var(--success-light)', color: 'var(--success)', borderColor: 'var(--success-border)' } : {}}>
                {language.toUpperCase()} {result.is_correct ? '• VALID' : ''}
              </span>
            </div>

            {/* If Code is Valid / Correct */}
            {result.is_correct ? (
              <div style={{
                background: 'var(--success-light)',
                border: '1px solid var(--success-border)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.85rem 1rem',
                marginBottom: '0.9rem'
              }}>
                <div style={{ fontSize: '0.82rem', fontWeight: '800', color: 'var(--success)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <CheckCircle size={16} /> Syntax & Logic Verification Passed
                </div>
                <div style={{ fontSize: '0.9rem', color: 'var(--text)', fontWeight: '600', lineHeight: '1.5' }}>
                  {result.explanation || 'Your code is clean, syntactically correct, and contains no detected defects.'}
                </div>
              </div>
            ) : (
              /* User Mistake Banner for Buggy Code */
              result.user_mistake && (
                <div className="user-mistake-banner" style={{
                  background: 'var(--danger-light)',
                  border: '1px solid var(--danger-border)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.85rem 1rem',
                  marginBottom: '0.9rem'
                }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: '800', color: 'var(--danger)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <AlertTriangle size={15} /> What You Did Wrong (User Mistake):
                  </div>
                  <div style={{ fontSize: '0.9rem', color: 'var(--text)', fontWeight: '600', lineHeight: '1.5' }}>
                    {result.user_mistake}
                  </div>
                </div>
              )
            )}

            {!result.is_correct && (
              <>
                <div className="diagnosis-text" style={{ marginBottom: '0.75rem' }}>
                  <strong style={{ color: 'var(--purple-accent)' }}>Technical Root Cause:</strong> {result.root_cause}
                </div>

                <div style={{ fontSize: '0.88rem', color: 'var(--text-muted)', marginBottom: '0.85rem', lineHeight: '1.5' }}>
                  <strong style={{ color: 'var(--accent)' }}>Fix Explanation:</strong> {result.explanation}
                </div>
              </>
            )}

            {/* Code Block */}
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                <span style={{ fontSize: '0.78rem', fontWeight: '700', textTransform: 'uppercase', color: 'var(--success)' }}>
                  {result.is_correct ? 'Verified Production Code:' : 'Corrected Production Code:'}
                </span>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                  onClick={handleCopyCode}
                >
                  <Copy size={12} /> {result.is_correct ? 'Copy Code' : 'Copy Corrected Code'}
                </button>
              </div>
              <pre className="reproduction-snippet" style={{ color: 'var(--success)' }}>
                {result.corrected_code}
              </pre>
              {copyToast && (
                <div style={{ fontSize: '0.78rem', color: 'var(--success)', marginTop: '0.35rem', fontWeight: '600' }}>
                  {copyToast}
                </div>
              )}
            </div>

            <div style={{ fontSize: '0.82rem', color: 'var(--accent)', background: 'var(--accent-light)', padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Lightbulb size={16} color="var(--accent)" />
              <span><strong>{result.is_correct ? 'Best Practice Tip:' : 'Prevention Tip:'}</strong> {result.prevention_tip}</span>
            </div>

            {/* Turn into Bug Issue Helper */}
            {projects.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', paddingTop: '0.85rem', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: '700', color: 'var(--text-muted)' }}>
                  Log into Project:
                </span>
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(Number(e.target.value))}
                  style={{ padding: '0.35rem 0.6rem', fontSize: '0.8rem', width: 'auto' }}
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleCreateIssueFromFix}
                  disabled={loggingIssue}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <BookmarkPlus size={14} />
                  {loggingIssue ? 'Creating Issue…' : 'Convert to Bug Issue'}
                </button>
                {issueCreatedNotice && (
                  <span style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: '600' }}>
                    {issueCreatedNotice}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
