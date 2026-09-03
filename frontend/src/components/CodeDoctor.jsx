import { useEffect, useState } from 'react';
import {
  Bot, Sparkles, AlertTriangle, Lightbulb, BookmarkPlus, Code,
  CheckCircle, Copy, Shield, Zap, Cpu, TestTube, GitCompare,
  FileCode, Layers, Lock, ShieldAlert, Check
} from 'lucide-react';
import { aiFixCode, createIssue } from '../api';

const BIG_TECH_SAMPLES = [
  {
    label: '🛡️ SQL Injection (CWE-89)',
    lang: 'python',
    profile: 'security',
    code: `def get_user_profile(user_id):\n    cursor = db.cursor()\n    query = f"SELECT id, username, email FROM users WHERE id = {user_id}"\n    cursor.execute(query)\n    return cursor.fetchone()`,
    err: `Vulnerability: Dynamic string interpolation in SQL query construction`,
  },
  {
    label: '⚡ Big-O O(N²) Quadratic Loop',
    lang: 'python',
    profile: 'performance',
    code: `def find_common_customers(list_a, list_b):\n    common = []\n    for cust_id in list_a:\n        if cust_id in list_b:\n            common.append(cust_id)\n    return common`,
    err: `Performance: Nested linear membership scan causes quadratic latency on large datasets`,
  },
  {
    label: '🔄 Async Race Condition on Counter',
    lang: 'python',
    profile: 'concurrency',
    code: `active_requests = 0\n\nasync def process_transaction(payload):\n    global active_requests\n    active_requests += 1\n    result = await execute_payment(payload)\n    active_requests -= 1\n    return result`,
    err: `Concurrency: Unsynchronized read-modify-write on shared mutable state`,
  },
  {
    label: '🧱 Resource Leak (Unclosed File)',
    lang: 'python',
    profile: 'resource_safety',
    code: `def parse_log_records(file_path):\n    f = open(file_path, "r")\n    data = f.read()\n    records = [json.loads(line) for line in data.splitlines()]\n    return records`,
    err: `Resource Leak: File descriptor unclosed if exception occurs during parsing`,
  },
  {
    label: '🧪 JS Null/Undefined .map() Crash',
    lang: 'javascript',
    profile: 'unit_tests',
    code: `const renderUserList = (props) => {\n  const users = props.data.users;\n  return users.map(user => user.name.toUpperCase());\n};`,
    err: `TypeError: Cannot read properties of undefined (reading 'map')`,
  },
  {
    label: '🐍 Python Syntax / Unclosed Quote',
    lang: 'python',
    profile: 'comprehensive',
    code: `print("hell)`,
    err: `SyntaxError: unterminated string literal (detected at line 1)`,
  },
];

export default function CodeDoctor({ projects = [], onIssueCreated }) {
  const [language, setLanguage] = useState('python');
  const [auditProfile, setAuditProfile] = useState('comprehensive');
  const [code, setCode] = useState('');
  const [sampleErr, setSampleErr] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [copyToast, setCopyToast] = useState('');
  const [activeTab, setActiveTab] = useState('code'); // 'code', 'diff', 'security', 'complexity', 'tests'
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
    setActiveTab('code');

    try {
      const res = await aiFixCode({
        code,
        error_log: sampleErr,
        language,
        audit_profile: auditProfile,
      });
      setResult(res);
      if (res.security_findings?.length > 0 && auditProfile === 'security') {
        setActiveTab('security');
      } else if (res.complexity_analysis && auditProfile === 'performance') {
        setActiveTab('complexity');
      } else if (res.generated_unit_tests && auditProfile === 'unit_tests') {
        setActiveTab('tests');
      }
    } catch (err) {
      setError(err.message || 'Failed to analyze code snippet');
    } finally {
      setLoading(false);
    }
  };

  const handleApplySample = (sample) => {
    setLanguage(sample.lang);
    setAuditProfile(sample.profile || 'comprehensive');
    setCode(sample.code);
    setSampleErr(sample.err || '');
    setResult(null);
    setError('');
  };

  const handleCopyCode = (textToCopy, label = 'Code') => {
    if (!textToCopy) return;
    navigator.clipboard.writeText(textToCopy);
    setCopyToast(`Copied ${label} to Clipboard!`);
    setTimeout(() => setCopyToast(''), 2500);
  };

  const handleCreateIssueFromFix = async () => {
    if (!selectedProjectId || !result) return;
    setLoggingIssue(true);
    try {
      const newIssue = await createIssue(selectedProjectId, {
        title: `Fix: ${result.root_cause.slice(0, 70)}`,
        description: `### AI Code Doctor Analysis (FAANG-Grade Audit)\n\n**Technical Root Cause:**\n${result.root_cause}\n\n**Explanation:**\n${result.explanation}\n\n### Original Code:\n\`\`\`${language}\n${code}\n\`\`\`\n\n### Corrected Production Code:\n\`\`\`${language}\n${result.corrected_code}\n\`\`\`\n\n${result.generated_unit_tests ? `### Generated Unit Tests:\n\`\`\`${language}\n${result.generated_unit_tests}\n\`\`\`` : ''}`,
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
            AI Code Doctor & Enterprise Intelligence Engine
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginTop: '0.2rem' }}>
            Principal Engineering-grade code diagnostics: Security (OWASP/CWE), Big-O Algorithmic Profiling, Thread Safety & Race Conditions, Resource Leaks, and Automated Test Generation.
          </p>
        </div>
      </div>

      {/* Preset FAANG Sample Chips */}
      <div style={{ marginBottom: '1.25rem' }}>
        <div style={{ fontSize: '0.78rem', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-dim)', marginBottom: '0.5rem' }}>
          Try Industry Scenarios (Amazon / Google / Meta Patterns):
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {BIG_TECH_SAMPLES.map((sample, idx) => (
            <button
              key={idx}
              type="button"
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '0.78rem' }}
              onClick={() => handleApplySample(sample)}
            >
              {sample.label}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleFixCode}>
        <div className="form-row" style={{ marginBottom: '1rem', display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '1rem' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label>Programming Language</label>
            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
              <option value="python">Python</option>
              <option value="javascript">JavaScript / React</option>
              <option value="typescript">TypeScript</option>
              <option value="sql">SQL / Relational DB</option>
              <option value="java">Java / JVM</option>
              <option value="go">Go / Golang</option>
              <option value="rust">Rust</option>
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Layers size={14} /> Diagnostic Lens / Audit Profile
            </label>
            <select value={auditProfile} onChange={(e) => setAuditProfile(e.target.value)}>
              <option value="comprehensive">🌐 Comprehensive Principal Engineering Review</option>
              <option value="security">🛡️ Security & Vulnerability Lens (OWASP / CWE)</option>
              <option value="performance">⚡ Performance & Big-O Complexity Lens</option>
              <option value="concurrency">🔄 Concurrency, Thread Safety & Race Conditions</option>
              <option value="resource_safety">🧱 Resource Safety & Leak Prevention (Context Managers)</option>
              <option value="unit_tests">🧪 Automated Unit & Regression Test Suite</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Code size={16} />
            Source Code Snippet to Diagnose & Optimize
          </label>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Paste function, query, or async handler to audit for security, Big-O complexity, thread-safety, and syntax..."
            rows={7}
            style={{ fontFamily: 'var(--mono)', fontSize: '0.86rem', lineHeight: '1.5' }}
            required
          />
        </div>

        {error && (
          <div className="error" style={{ marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          className="btn btn-ai"
          style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', padding: '0.75rem' }}
          disabled={loading || !code.trim()}
        >
          {loading ? (
            <>
              <div className="spinner" style={{ width: '18px', height: '18px', borderWidth: '2px' }} />
              Running Multi-Perspective Audit & Code Optimization…
            </>
          ) : (
            <>
              <Sparkles size={16} />
              Run Code Doctor Intelligence Audit
            </>
          )}
        </button>
      </form>

      {/* AI Doctor Enterprise Result View */}
      {result && (
        <div style={{ marginTop: '1.5rem', paddingTop: '1.25rem', borderTop: '1px solid var(--border)' }}>
          <div className="copilot-diagnosis-box" style={{ marginTop: 0 }}>
            {/* Header & Badges */}
            <div className="copilot-header" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
              <div className="copilot-title" style={{ color: result.is_correct ? 'var(--success)' : 'var(--accent)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <CheckCircle size={18} color={result.is_correct ? 'var(--success)' : 'var(--accent)'} />
                {result.is_correct ? 'Code Verified & Production Ready' : 'Defect Diagnosed & Remediation Ready'}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
                {result.ast_verified && (
                  <span className="badge badge-resolved" style={{ fontSize: '0.72rem' }}>✓ AST VERIFIED</span>
                )}
                {result.complexity_analysis && (
                  <span className="badge" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', fontSize: '0.72rem' }}>
                    ⚡ {result.complexity_analysis.time_complexity_original} ➔ {result.complexity_analysis.time_complexity_optimized}
                  </span>
                )}
                {result.security_findings?.length > 0 && (
                  <span className="badge badge-severity badge-critical" style={{ fontSize: '0.72rem' }}>
                    🛡️ {result.security_findings.length} SECURITY ISSUE{result.security_findings.length > 1 ? 'S' : ''}
                  </span>
                )}
                <span className="layer-tag">
                  {language.toUpperCase()} • {auditProfile.toUpperCase()}
                </span>
              </div>
            </div>

            {/* User Mistake & Technical Root Cause */}
            {result.user_mistake && (
              <div style={{
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.8rem 1rem',
                marginBottom: '0.85rem'
              }}>
                <div style={{ fontSize: '0.78rem', fontWeight: '800', color: '#ef4444', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <AlertTriangle size={15} /> What Caused The Defect:
                </div>
                <div style={{ fontSize: '0.88rem', color: 'var(--text)', fontWeight: '600', lineHeight: '1.5' }}>
                  {result.user_mistake}
                </div>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem', marginBottom: '1rem' }}>
              <div style={{ background: 'var(--bg-dark)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '0.75rem 0.9rem' }}>
                <strong style={{ color: 'var(--purple-accent)', fontSize: '0.82rem', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'block', marginBottom: '0.25rem' }}>
                  🔍 Technical Root Cause:
                </strong>
                <span style={{ fontSize: '0.86rem', color: 'var(--text)', lineHeight: '1.45' }}>{result.root_cause}</span>
              </div>
              <div style={{ background: 'var(--bg-dark)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '0.75rem 0.9rem' }}>
                <strong style={{ color: 'var(--accent)', fontSize: '0.82rem', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'block', marginBottom: '0.25rem' }}>
                  💡 Engineering Fix Explanation:
                </strong>
                <span style={{ fontSize: '0.86rem', color: 'var(--text)', lineHeight: '1.45' }}>{result.explanation}</span>
              </div>
            </div>

            {/* Diagnostic Tabs Navigation */}
            <div style={{ display: 'flex', gap: '0.4rem', borderBottom: '1px solid var(--border)', paddingBottom: '0.4rem', marginBottom: '0.85rem', flexWrap: 'wrap' }}>
              <button
                type="button"
                className={`btn btn-sm ${activeTab === 'code' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab('code')}
                style={{ fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
              >
                <FileCode size={14} /> Corrected Code
              </button>
              {result.diff_lines?.length > 0 && (
                <button
                  type="button"
                  className={`btn btn-sm ${activeTab === 'diff' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('diff')}
                  style={{ fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <GitCompare size={14} /> Line Diff ({result.diff_lines.length})
                </button>
              )}
              {result.security_findings?.length > 0 && (
                <button
                  type="button"
                  className={`btn btn-sm ${activeTab === 'security' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('security')}
                  style={{ fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '0.35rem', color: '#ef4444' }}
                >
                  <ShieldAlert size={14} /> Security Audit ({result.security_findings.length})
                </button>
              )}
              {result.complexity_analysis && (
                <button
                  type="button"
                  className={`btn btn-sm ${activeTab === 'complexity' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('complexity')}
                  style={{ fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <Zap size={14} /> Big-O Complexity
                </button>
              )}
              {result.generated_unit_tests && (
                <button
                  type="button"
                  className={`btn btn-sm ${activeTab === 'tests' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('tests')}
                  style={{ fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  <TestTube size={14} /> Automated Unit Tests
                </button>
              )}
            </div>

            {/* TAB 1: Corrected Code View */}
            {activeTab === 'code' && (
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: '700', textTransform: 'uppercase', color: 'var(--success)' }}>
                    {result.is_correct ? 'Verified Production Code:' : 'Corrected Production-Ready Code:'}
                  </span>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                    onClick={() => handleCopyCode(result.corrected_code, 'Corrected Code')}
                  >
                    <Copy size={12} /> {result.is_correct ? 'Copy Code' : 'Copy Corrected Code'}
                  </button>
                </div>
                <pre className="reproduction-snippet" style={{ color: 'var(--success)', maxHeight: '350px', overflowY: 'auto' }}>
                  {result.corrected_code}
                </pre>
              </div>
            )}

            {/* TAB 2: Unified Diff View */}
            {activeTab === 'diff' && (
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: '700', textTransform: 'uppercase', color: 'var(--accent)' }}>
                    Unified Code Diff (Original vs Corrected):
                  </span>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                    onClick={() => handleCopyCode(result.diff_lines.map(l => l.text).join('\n'), 'Diff')}
                  >
                    <Copy size={12} /> Copy Diff
                  </button>
                </div>
                <div style={{
                  background: '#0d1117',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)',
                  fontFamily: 'var(--mono)',
                  fontSize: '0.82rem',
                  padding: '0.6rem 0.8rem',
                  maxHeight: '350px',
                  overflowY: 'auto',
                  lineHeight: '1.5'
                }}>
                  {result.diff_lines.map((dl, dIdx) => (
                    <div
                      key={dIdx}
                      style={{
                        color: dl.type === 'add' ? '#34d399' : dl.type === 'del' ? '#f87171' : dl.type === 'info' ? '#93c5fd' : 'var(--text-muted)',
                        background: dl.type === 'add' ? 'rgba(52, 211, 153, 0.1)' : dl.type === 'del' ? 'rgba(248, 113, 113, 0.1)' : 'transparent',
                        padding: '0.15rem 0.35rem',
                        borderRadius: '2px',
                        whiteSpace: 'pre-wrap'
                      }}
                    >
                      {dl.text}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 3: Security Findings View */}
            {activeTab === 'security' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', marginBottom: '1rem' }}>
                {result.security_findings.map((sec, sIdx) => (
                  <div
                    key={sIdx}
                    style={{
                      background: 'rgba(239, 68, 68, 0.06)',
                      border: '1px solid rgba(239, 68, 68, 0.25)',
                      borderRadius: 'var(--radius-md)',
                      padding: '0.85rem 1rem'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                      <strong style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.9rem' }}>
                        <ShieldAlert size={16} /> {sec.cwe_id ? `${sec.cwe_id}: ` : ''}{sec.title}
                      </strong>
                      <span className="badge badge-severity badge-critical" style={{ fontSize: '0.72rem' }}>
                        {sec.severity}
                      </span>
                    </div>
                    <p style={{ margin: '0 0 0.4rem 0', fontSize: '0.85rem', color: 'var(--text)', lineHeight: '1.5' }}>
                      {sec.description}
                    </p>
                    <div style={{ background: 'var(--bg-dark)', padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-sm)', fontSize: '0.82rem', color: '#34d399' }}>
                      <strong>Remediation:</strong> {sec.remediation}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* TAB 4: Complexity Analysis View */}
            {activeTab === 'complexity' && result.complexity_analysis && (
              <div style={{ background: 'var(--bg-dark)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '1rem', marginBottom: '1rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', marginBottom: '0.75rem' }}>
                  <div style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)', padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Time Complexity</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '800', color: '#f59e0b', marginTop: '0.2rem' }}>
                      {result.complexity_analysis.time_complexity_original} ➔ {result.complexity_analysis.time_complexity_optimized}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.2)', padding: '0.65rem 0.85rem', borderRadius: 'var(--radius-sm)' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textTransform: 'uppercase' }}>Space Complexity</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: '800', color: '#38bdf8', marginTop: '0.2rem' }}>
                      {result.complexity_analysis.space_complexity_original} ➔ {result.complexity_analysis.space_complexity_optimized}
                    </div>
                  </div>
                </div>
                <p style={{ margin: 0, fontSize: '0.86rem', color: 'var(--text)', lineHeight: '1.55' }}>
                  <strong>Bottleneck Analysis:</strong> {result.complexity_analysis.bottleneck_explanation}
                </p>
              </div>
            )}

            {/* TAB 5: Automated Unit Tests View */}
            {activeTab === 'tests' && result.generated_unit_tests && (
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: '700', textTransform: 'uppercase', color: 'var(--accent)' }}>
                    Generated Unit & Regression Test Suite:
                  </span>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ padding: '0.2rem 0.55rem', fontSize: '0.72rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                    onClick={() => handleCopyCode(result.generated_unit_tests, 'Unit Tests')}
                  >
                    <Copy size={12} /> Copy Test Suite
                  </button>
                </div>
                <pre className="reproduction-snippet" style={{ color: '#93c5fd', maxHeight: '350px', overflowY: 'auto' }}>
                  {result.generated_unit_tests}
                </pre>
              </div>
            )}

            {copyToast && (
              <div style={{ fontSize: '0.78rem', color: 'var(--success)', marginBottom: '0.6rem', fontWeight: '600' }}>
                {copyToast}
              </div>
            )}

            {/* Best Practice Tip & Resilience Patterns */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.82rem', color: 'var(--accent)', background: 'var(--accent-light)', padding: '0.65rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Lightbulb size={16} color="var(--accent)" style={{ flexShrink: 0 }} />
                <span><strong>{result.is_correct ? 'Best Practice Tip:' : 'Prevention Tip:'}</strong> {result.prevention_tip}</span>
              </div>

              {result.resilience_patterns?.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-dim)' }}>Applied Resilience Patterns:</span>
                  {result.resilience_patterns.map((pat, pIdx) => (
                    <span key={pIdx} className="badge" style={{ background: 'rgba(59, 130, 246, 0.12)', color: '#60a5fa', fontSize: '0.72rem' }}>
                      ✓ {pat}
                    </span>
                  ))}
                </div>
              )}
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
