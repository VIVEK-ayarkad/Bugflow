import React, { useEffect, useState, useMemo } from 'react';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Boxes,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Cpu,
  Database,
  ExternalLink,
  Filter,
  Flame,
  Globe,
  Info,
  Layers,
  LayoutGrid,
  Lock,
  RefreshCw,
  Search,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  Users,
  Workflow,
  Zap,
} from 'lucide-react';
import { getProjectBlastRadius } from '../api';

const MODULE_ICONS = {
  // Security / Auth
  auth_rbac: Lock,
  auth_accounts: Lock,
  auth_iam: Lock,
  auth_security: Lock,
  auth_vault: Lock,
  auth: Lock,

  // Client / UI
  client_dashboard: Layers,
  storefront: ShoppingBag,
  data_portal: Database,
  client_app: Users,
  cli_console: Cpu,
  user_profile: Users,
  user_graph: Users,

  // Gateway / Ingress
  api_gateway: Cpu,

  // Core Engines
  task_engine: Workflow,
  cart_checkout: ShoppingBag,
  checkout: ShoppingBag,
  ingestion_pipeline: RefreshCw,
  feed_engine: Activity,
  runner_engine: Zap,
  product_catalog: Database,
  inventory: Database,

  // Finance / Payments
  payment_gateway: Flame,
  payment: Flame,
  subscription: RefreshCw,

  // Storage / Persistence
  data_lake: Database,
  artifact_registry: Database,
  media_cdn: Database,
  attachment_store: Database,

  // Analytics & Metrics
  sprint_analytics: Activity,
  analytics: Activity,
  telemetry: Activity,
  observability: Activity,
  query_engine: Cpu,
  search_engine: Search,
  search_discovery: Search,

  // AI & ML
  ai_copilot: Sparkles,
  ml_inference: Sparkles,

  // Alerts & Messaging
  notification_service: Globe,
  notifications: Globe,
  push_service: Globe,
  alerting_monitor: AlertTriangle,
  webhook_dispatcher: Globe,

  // Compliance & Infra
  audit_logger: Shield,
  moderation: Shield,
  order_fulfillment: CheckCircle2,
  cluster_agent: Server,
};

const CANONICAL_POSITIONS = {
  // SaaS & Workflow
  client_dashboard: { x: 170, y: 75 },
  api_gateway: { x: 430, y: 75 },
  auth_rbac: { x: 690, y: 75 },
  task_engine: { x: 430, y: 220 },
  sprint_analytics: { x: 170, y: 220 },
  ai_copilot: { x: 690, y: 220 },
  attachment_store: { x: 170, y: 375 },
  notification_service: { x: 430, y: 375 },
  audit_logger: { x: 690, y: 375 },

  // E-Commerce
  storefront: { x: 430, y: 70 },
  auth_accounts: { x: 190, y: 150 },
  product_catalog: { x: 670, y: 150 },
  cart_checkout: { x: 430, y: 210 },
  payment_gateway: { x: 430, y: 340 },
  order_fulfillment: { x: 210, y: 440 },
  notifications: { x: 430, y: 460 },
  analytics: { x: 650, y: 440 },

  // Data & AI
  data_portal: { x: 170, y: 75 },
  auth_iam: { x: 690, y: 75 },
  ingestion_pipeline: { x: 170, y: 220 },
  query_engine: { x: 430, y: 220 },
  ml_inference: { x: 690, y: 220 },
  data_lake: { x: 260, y: 380 },
  alerting_monitor: { x: 600, y: 380 },
  telemetry: { x: 430, y: 465 },

  // Social & Community
  client_app: { x: 170, y: 75 },
  auth_security: { x: 690, y: 75 },
  feed_engine: { x: 430, y: 210 },
  user_graph: { x: 170, y: 220 },
  search_discovery: { x: 690, y: 220 },
  media_cdn: { x: 170, y: 380 },
  moderation: { x: 430, y: 380 },
  push_service: { x: 690, y: 380 },

  // DevOps & Cloud
  cli_console: { x: 170, y: 75 },
  auth_vault: { x: 690, y: 75 },
  runner_engine: { x: 430, y: 210 },
  artifact_registry: { x: 170, y: 360 },
  cluster_agent: { x: 430, y: 360 },
  webhook_dispatcher: { x: 690, y: 360 },
  observability: { x: 430, y: 465 },

  // Legacy Aliases
  auth: { x: 190, y: 150 },
  checkout: { x: 430, y: 210 },
  payment: { x: 430, y: 340 },
  subscription: { x: 210, y: 440 },
  inventory: { x: 670, y: 150 },
  user_profile: { x: 190, y: 280 },
  search_engine: { x: 670, y: 280 },
};

function getNodePosition(nodeId, index, totalNodes) {
  if (CANONICAL_POSITIONS[nodeId]) {
    return CANONICAL_POSITIONS[nodeId];
  }
  const cols = 3;
  const col = index % cols;
  const row = Math.floor(index / cols);
  return {
    x: 170 + col * 260,
    y: 80 + row * 150,
  };
}

export default function BlastRadiusVisualizer({
  projectId,
  initialFocusedIssueId = null,
  issues = [],
  onSelectIssue = null,
  embedded = false,
}) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [focusedIssueId, setFocusedIssueId] = useState(initialFocusedIssueId);
  const [selectedDomain, setSelectedDomain] = useState('auto');
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [hoveredNodeId, setHoveredNodeId] = useState(null);
  const [matrixSearch, setMatrixSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [moduleFilter, setModuleFilter] = useState('all');
  const [showBeginnerGuide, setShowBeginnerGuide] = useState(true);
  const [expandedDefectIds, setExpandedDefectIds] = useState({});

  useEffect(() => {
    if (initialFocusedIssueId) {
      setFocusedIssueId(initialFocusedIssueId);
    }
  }, [initialFocusedIssueId]);

  useEffect(() => {
    if (projectId) {
      loadBlastRadius(projectId, focusedIssueId, selectedDomain);
    }
  }, [projectId, focusedIssueId, selectedDomain]);

  async function loadBlastRadius(pId, issueId, domain = 'auto') {
    setLoading(true);
    try {
      const data = await getProjectBlastRadius(pId, issueId, domain);
      setReport(data);
      if (data.focused_module_id) {
        setSelectedNodeId(data.focused_module_id);
      } else if (data.nodes?.length > 0 && (!selectedNodeId || !data.nodes.some((n) => n.id === selectedNodeId))) {
        const firstEpicenter = data.nodes.find((n) => n.is_epicenter || n.open_defects_count > 0);
        setSelectedNodeId(firstEpicenter ? firstEpicenter.id : data.nodes[0].id);
      }
    } catch (err) {
      console.error('Failed to load blast radius:', err);
    } finally {
      setLoading(false);
    }
  }

  const selectedNode = useMemo(() => {
    if (!report?.nodes) return null;
    return report.nodes.find((n) => n.id === selectedNodeId) || report.nodes[0];
  }, [report, selectedNodeId]);

  const availableModules = useMemo(() => {
    if (!report?.nodes) return [];
    return report.nodes.map((n) => ({ id: n.id, name: n.name, open_defects_count: n.open_defects_count }));
  }, [report]);

  const activeEdges = useMemo(() => {
    if (!report?.edges) return [];
    const targetId = hoveredNodeId || selectedNodeId;
    if (!targetId) return [];
    return report.edges.filter((e) => e.source === targetId || e.target === targetId);
  }, [report, selectedNodeId, hoveredNodeId]);

  // Find upstream defects that cause issues in the currently selected module
  const incomingThreats = useMemo(() => {
    if (!report?.defect_allocations || !selectedNode) return [];
    const threats = [];
    for (const alloc of report.defect_allocations) {
      if (alloc.allocated_module_id === selectedNode.id) continue;
      const matchingCaused = alloc.caused_issues?.find((ci) => ci.target_module_id === selectedNode.id);
      if (matchingCaused) {
        threats.push({
          defect_id: alloc.defect_id,
          defect_title: alloc.title,
          severity: alloc.severity,
          origin_module_id: alloc.allocated_module_id,
          origin_module_name: alloc.allocated_module_name,
          impact_level: matchingCaused.impact_level,
          failure_description: matchingCaused.failure_description,
          affected_defect_ids: matchingCaused.affected_defect_ids || [],
        });
      }
    }
    return threats;
  }, [report, selectedNode]);

  // Filter defect allocations for the matrix table
  const filteredAllocations = useMemo(() => {
    if (!report?.defect_allocations) return [];
    return report.defect_allocations.filter((item) => {
      const matchesSev = severityFilter === 'all' || item.severity.toLowerCase() === severityFilter.toLowerCase();
      const matchesMod = moduleFilter === 'all' || item.allocated_module_id === moduleFilter;
      const query = matrixSearch.toLowerCase().trim();
      if (!query) return matchesSev && matchesMod;

      const matchesQuery =
        item.title.toLowerCase().includes(query) ||
        item.allocated_module_name.toLowerCase().includes(query) ||
        (item.allocation_reason && item.allocation_reason.toLowerCase().includes(query)) ||
        `#def-${item.defect_id}`.toLowerCase().includes(query) ||
        `${item.defect_id}`.includes(query) ||
        item.caused_issues?.some((ci) =>
          ci.target_module_name.toLowerCase().includes(query) ||
          ci.failure_description.toLowerCase().includes(query)
        );

      return matchesSev && matchesMod && matchesQuery;
    });
  }, [report, matrixSearch, severityFilter, moduleFilter]);

  const toggleExpandDefect = (dId) => {
    setExpandedDefectIds((prev) => ({
      ...prev,
      [dId]: !prev[dId],
    }));
  };

  if (loading && !report) {
    return (
      <div style={{ padding: '3.5rem 2rem', textAlign: 'center', background: 'var(--surface)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
        <RefreshCw size={36} className="text-accent spin" style={{ margin: '0 auto 1rem' }} />
        <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>Autonomously Synthesizing Blast Radius Map...</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: '0.35rem 0 0' }}>
          Mapping project workflow topology, auto-allocating defects to components, and tracing cascading downstream failure paths.
        </p>
      </div>
    );
  }

  if (!report) {
    return (
      <div style={{ padding: '3rem', textAlign: 'center', background: 'var(--surface)', borderRadius: 'var(--radius)', border: '1px dashed var(--border)' }}>
        <ShieldAlert size={36} style={{ color: 'var(--text-muted)', margin: '0 auto 0.75rem' }} />
        <h4 style={{ margin: '0 0 0.5rem' }}>No Architecture Topology Available</h4>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Select an active project with logged defects to compute failure blast radius.</p>
      </div>
    );
  }

  const blastScoreColor =
    report.system_blast_score >= 75
      ? '#ef4444'
      : report.system_blast_score >= 50
      ? '#f97316'
      : report.system_blast_score >= 25
      ? '#eab308'
      : '#10b981';

  const totalEpicenters = report.nodes?.filter((n) => n.is_epicenter || n.open_defects_count > 0).length || 0;
  const isAutonomousMode = !focusedIssueId;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* ── Autonomous Mode Banner & Ribbon ─────────────────────────────────── */}
      <div
        style={{
          background: 'var(--surface)',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--border)',
          padding: '1.25rem 1.5rem',
          boxShadow: 'var(--shadow-soft)',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap', marginBottom: '0.2rem' }}>
              <h2
                style={{
                  margin: 0,
                  fontSize: embedded ? '1.15rem' : '1.35rem',
                  fontWeight: 800,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  fontFamily: 'var(--display)',
                }}
              >
                <Zap size={22} color="var(--accent)" />
                Bug Blast-Radius &amp; Architecture Dependency Visualizer
              </h2>

              <span
                className="badge"
                style={{
                  background: 'var(--accent-light)',
                  color: 'var(--accent)',
                  borderColor: 'var(--border)',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  padding: '0.25rem 0.65rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                }}
              >
                <Boxes size={13} /> {report.domain_archetype}
              </span>

              <span
                className="badge"
                style={{
                  background: isAutonomousMode ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                  color: isAutonomousMode ? '#10b981' : '#ef4444',
                  borderColor: isAutonomousMode ? '#10b981' : '#ef4444',
                  fontSize: '0.78rem',
                  fontWeight: 800,
                  padding: '0.25rem 0.65rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                }}
              >
                <Sparkles size={13} /> {isAutonomousMode ? '⚡ Autonomous Defect Impact Allocation Active' : `Spotlight: Defect #${focusedIssueId}`}
              </span>
            </div>

            <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Project: <strong style={{ color: 'var(--text)' }}>{report.project_name}</strong> • Computes which components each defect impacts and traces cascading failure paths.
            </p>
          </div>

          {/* Controls: Domain Blueprint Override + Spotlight Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            {/* Architecture Domain Switcher */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Topology:
              </label>
              <select
                value={selectedDomain}
                onChange={(e) => setSelectedDomain(e.target.value)}
                style={{
                  padding: '0.4rem 0.75rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-dark-accent)',
                  color: 'var(--text)',
                  fontWeight: 600,
                  fontSize: '0.82rem',
                }}
              >
                {(report.available_archetypes || []).map((arch) => (
                  <option key={arch.id} value={arch.id}>
                    {arch.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Focus / Spotlight Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Mode:
              </label>
              <select
                value={focusedIssueId || ''}
                onChange={(e) => setFocusedIssueId(e.target.value ? parseInt(e.target.value) : null)}
                style={{
                  padding: '0.4rem 0.75rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-dark-accent)',
                  color: 'var(--text)',
                  fontWeight: 600,
                  fontSize: '0.82rem',
                  maxWidth: '260px',
                }}
              >
                <option value="">⚡ All Defects (Auto-Allocated System Map)</option>
                {issues.map((i) => (
                  <option key={i.id} value={i.id}>
                    Spotlight #{i.id} [{i.severity.toUpperCase()}] {i.title.slice(0, 30)}
                  </option>
                ))}
              </select>

              {!isAutonomousMode && (
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => setFocusedIssueId(null)}
                  title="Reset to Full Autonomous System Map"
                  style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
                >
                  Show All
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Top KPI Ribbon */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem' }}>
          {/* Blast Score Gauge */}
          <div style={{ background: 'var(--bg-dark-accent)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>System Blast Score</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: blastScoreColor, marginTop: '0.1rem', display: 'flex', alignItems: 'baseline', gap: '0.35rem' }}>
              {report.system_blast_score}%
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>({report.overall_status})</span>
            </div>
            <div style={{ height: '5px', background: 'var(--border)', borderRadius: '3px', marginTop: '0.4rem', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${report.system_blast_score}%`, background: blastScoreColor, transition: 'width 0.4s ease' }} />
            </div>
          </div>

          {/* Failure Epicenters */}
          <div style={{ background: 'var(--bg-dark-accent)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Failure Epicenters</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#ef4444', marginTop: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <Flame size={16} /> {isAutonomousMode ? `${totalEpicenters} Hotspot Modules` : (report.epicenter_module || 'None Identified')}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              {isAutonomousMode ? `${report.defect_allocations?.length || 0} defects auto-allocated` : (report.focused_issue_title ? `#${report.focused_issue_id} • ${report.focused_issue_title.slice(0, 22)}...` : 'Single bug view')}
            </div>
          </div>

          {/* Direct Impact Count */}
          <div style={{ background: 'var(--bg-dark-accent)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Direct Impact Zone</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#f97316', marginTop: '0.1rem' }}>
              {report.direct_impact_count} Modules
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              1st-degree callers compromised
            </div>
          </div>

          {/* Cascading Risk Count */}
          <div style={{ background: 'var(--bg-dark-accent)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Cascading Failure Risk</div>
            <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#eab308', marginTop: '0.1rem' }}>
              {report.cascade_risk_count} Modules
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              2nd-degree transitive impact
            </div>
          </div>
        </div>
      </div>

      {/* ── Friendly Beginner Guide / Interactive Explainer ─────────────── */}
      <div
        style={{
          background: 'var(--surface)',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--border)',
          padding: '1.15rem 1.4rem',
          boxShadow: 'var(--shadow-soft)',
        }}
      >
        <div
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
          onClick={() => setShowBeginnerGuide(!showBeginnerGuide)}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{ background: 'var(--accent-light)', padding: '0.4rem', borderRadius: '8px', color: 'var(--accent)', display: 'flex' }}>
              <Info size={18} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 800, color: 'var(--text)' }}>
                👶 Beginner's Visual Guide: Understanding Bug Blast-Radius
              </h3>
              <p style={{ margin: '0.15rem 0 0', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                How defects in one module propagate across connected components in real time.
              </p>
            </div>
          </div>
          <button
            type="button"
            style={{
              background: 'var(--bg-dark-accent)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              padding: '0.3rem 0.65rem',
              fontSize: '0.75rem',
              fontWeight: 700,
              color: 'var(--text)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
          >
            {showBeginnerGuide ? 'Hide Guide' : 'Show Guide'}
            {showBeginnerGuide ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        </div>

        {showBeginnerGuide && (
          <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.85rem', borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
            {/* 4 Concept Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '0.75rem' }}>
              {/* Step 1 */}
              <div style={{ background: 'var(--bg-dark-accent)', padding: '0.75rem 0.9rem', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.3)', borderLeft: '4px solid #ef4444' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.3rem' }}>
                  <span style={{ background: '#ef4444', color: '#fff', fontSize: '0.68rem', fontWeight: 900, borderRadius: '50%', width: '18px', height: '18px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>1</span>
                  <strong style={{ fontSize: '0.84rem', color: '#ef4444' }}>🔴 Defect Epicenter</strong>
                </div>
                <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--text)', lineHeight: 1.4 }}>
                  <strong>Where the bug lives.</strong> The defect is reported directly inside this component (e.g. Auth, Dashboard, or File Store).
                </p>
              </div>

              {/* Step 2 */}
              <div style={{ background: 'var(--bg-dark-accent)', padding: '0.75rem 0.9rem', borderRadius: '8px', border: '1px solid rgba(249, 115, 22, 0.3)', borderLeft: '4px solid #f97316' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.3rem' }}>
                  <span style={{ background: '#f97316', color: '#fff', fontSize: '0.68rem', fontWeight: 900, borderRadius: '50%', width: '18px', height: '18px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>2</span>
                  <strong style={{ fontSize: '0.84rem', color: '#f97316' }}>🟠 Direct Impact (1st-Deg)</strong>
                </div>
                <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--text)', lineHeight: 1.4 }}>
                  <strong>Immediate breakages.</strong> Connected services that call the broken component directly will start failing immediately.
                </p>
              </div>

              {/* Step 3 */}
              <div style={{ background: 'var(--bg-dark-accent)', padding: '0.75rem 0.9rem', borderRadius: '8px', border: '1px solid rgba(234, 179, 8, 0.3)', borderLeft: '4px solid #eab308' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.3rem' }}>
                  <span style={{ background: '#eab308', color: '#fff', fontSize: '0.68rem', fontWeight: 900, borderRadius: '50%', width: '18px', height: '18px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>3</span>
                  <strong style={{ fontSize: '0.84rem', color: '#eab308' }}>🟡 Cascade Risk (2nd-Deg)</strong>
                </div>
                <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--text)', lineHeight: 1.4 }}>
                  <strong>Domino effect.</strong> Secondary components further down the chain that experience latency spikes, timeouts, or degraded data.
                </p>
              </div>

              {/* Step 4 */}
              <div style={{ background: 'var(--bg-dark-accent)', padding: '0.75rem 0.9rem', borderRadius: '8px', border: '1px solid rgba(16, 185, 129, 0.3)', borderLeft: '4px solid #10b981' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.3rem' }}>
                  <span style={{ background: '#10b981', color: '#fff', fontSize: '0.68rem', fontWeight: 900, borderRadius: '50%', width: '18px', height: '18px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>4</span>
                  <strong style={{ fontSize: '0.84rem', color: '#10b981' }}>🟢 Safe Modules</strong>
                </div>
                <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--text)', lineHeight: 1.4 }}>
                  <strong>Unaffected.</strong> These components are isolated from the failure path and operate with 100% nominal integrity.
                </p>
              </div>
            </div>

            {/* Quick interactive tip */}
            <div style={{ background: 'rgba(99, 102, 241, 0.08)', padding: '0.6rem 0.9rem', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.25)', fontSize: '0.78rem', color: 'var(--text)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sparkles size={16} color="var(--accent)" style={{ flexShrink: 0 }} />
              <span>
                <strong>Interactive Tip:</strong> Click any component box on the map below or click <strong>"Spotlight on Map"</strong> on any defect in the table to see its exact animated failure path and containment actions!
              </span>
            </div>
          </div>
        )}
      </div>

      {/* ── Autonomous Defect Allocation & Impact Propagation Matrix ─────────── */}
      <div
        style={{
          background: 'var(--surface)',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--border)',
          padding: '1.25rem 1.5rem',
          boxShadow: 'var(--shadow-soft)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
              <Workflow size={18} className="text-accent" />
              <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800 }}>
                Defect Allocation &amp; Downstream Failure Matrix
              </h3>
              <span className="badge" style={{ background: 'var(--bg-dark-accent)', border: '1px solid var(--border)', fontSize: '0.72rem' }}>
                {report.defect_allocations?.length || 0} Total Defects
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Each defect is properly allocated to its host architectural component with clear allocation rationale and secondary systems threatened.
            </p>
          </div>

          {/* Search, Module & Severity Filters */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            {/* Module Filter Dropdown */}
            <select
              value={moduleFilter}
              onChange={(e) => setModuleFilter(e.target.value)}
              style={{
                padding: '0.35rem 0.65rem',
                fontSize: '0.78rem',
                borderRadius: '6px',
                border: '1px solid var(--border)',
                background: 'var(--bg-dark-accent)',
                color: 'var(--text)',
                fontWeight: 600,
                maxWidth: '180px',
              }}
            >
              <option value="all">All Components ({report.defect_allocations?.length || 0})</option>
              {availableModules.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({report.defect_allocations?.filter((a) => a.allocated_module_id === m.id).length || 0})
                </option>
              ))}
            </select>

            {/* Search Input */}
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search defects, modules, keywords..."
                value={matrixSearch}
                onChange={(e) => setMatrixSearch(e.target.value)}
                style={{
                  padding: '0.35rem 0.75rem 0.35rem 2rem',
                  fontSize: '0.8rem',
                  borderRadius: '6px',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-dark-accent)',
                  color: 'var(--text)',
                  width: '180px',
                }}
              />
            </div>

            {/* Severity Tabs */}
            <div style={{ display: 'flex', gap: '0.25rem' }}>
              {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  style={{
                    padding: '0.3rem 0.55rem',
                    fontSize: '0.72rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border)',
                    background: severityFilter === sev ? 'var(--accent)' : 'var(--bg-dark-accent)',
                    color: severityFilter === sev ? '#ffffff' : 'var(--text-muted)',
                    fontWeight: 700,
                    textTransform: 'capitalize',
                    cursor: 'pointer',
                  }}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Matrix List / Cards */}
        {filteredAllocations.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No defects found matching the selected filter criteria.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', maxHeight: '380px', overflowY: 'auto', paddingRight: '0.25rem' }}>
            {filteredAllocations.map((alloc) => {
              const isExpanded = !!expandedDefectIds[alloc.defect_id];
              const isSpotlighted = focusedIssueId === alloc.defect_id;
              const sevColor =
                alloc.severity === 'critical'
                  ? '#ef4444'
                  : alloc.severity === 'high'
                  ? '#f97316'
                  : alloc.severity === 'medium'
                  ? '#eab308'
                  : '#10b981';

              const ModuleIcon = MODULE_ICONS[alloc.allocated_module_id] || Layers;

              return (
                <div
                  key={alloc.defect_id}
                  style={{
                    background: isSpotlighted ? 'rgba(2, 132, 199, 0.08)' : 'var(--bg-dark-accent)',
                    borderRadius: '8px',
                    border: isSpotlighted ? '1.5px solid var(--accent)' : '1px solid var(--border)',
                    padding: '0.85rem 1rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.55rem',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
                      <span
                        className="badge"
                        style={{
                          background: `${sevColor}20`,
                          color: sevColor,
                          borderColor: sevColor,
                          fontSize: '0.72rem',
                          fontWeight: 800,
                          padding: '0.2rem 0.5rem',
                        }}
                      >
                        #{alloc.defect_id} • {alloc.severity.toUpperCase()}
                      </span>

                      <strong
                        style={{ fontSize: '0.88rem', color: 'var(--text)', cursor: onSelectIssue ? 'pointer' : 'default' }}
                        onClick={() => {
                          const orig = issues.find((i) => i.id === alloc.defect_id);
                          if (orig && onSelectIssue) onSelectIssue(orig);
                        }}
                        title="Click to view defect details"
                      >
                        {alloc.title}
                      </strong>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {/* Properly Allocated Component Pill */}
                      <span
                        style={{
                          background: 'var(--surface)',
                          border: '1px solid var(--border)',
                          borderRadius: '6px',
                          padding: '0.25rem 0.55rem',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          color: 'var(--text)',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.35rem',
                        }}
                      >
                        <ModuleIcon size={13} color="var(--accent)" />
                        Allocated to: <strong>{alloc.allocated_module_name}</strong>
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>({alloc.allocation_confidence}% conf)</span>
                      </span>

                      {/* Spotlight in Graph Button */}
                      <button
                        onClick={() => {
                          if (focusedIssueId === alloc.defect_id) {
                            setFocusedIssueId(null);
                          } else {
                            setFocusedIssueId(alloc.defect_id);
                            setSelectedNodeId(alloc.allocated_module_id);
                          }
                        }}
                        style={{
                          background: isSpotlighted ? 'var(--accent)' : 'var(--surface)',
                          color: isSpotlighted ? '#ffffff' : 'var(--text)',
                          border: '1px solid var(--border)',
                          borderRadius: '6px',
                          padding: '0.25rem 0.55rem',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.3rem',
                        }}
                      >
                        <Flame size={12} color={isSpotlighted ? '#ffffff' : '#ef4444'} />
                        {isSpotlighted ? 'Release Spotlight' : 'Spotlight on Map'}
                      </button>

                      <button
                        onClick={() => toggleExpandDefect(alloc.defect_id)}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: 'var(--text-muted)',
                          cursor: 'pointer',
                          padding: '0.2rem',
                          display: 'inline-flex',
                          alignItems: 'center',
                        }}
                        title={isExpanded ? 'Collapse Impact Breakdown' : 'Expand Impact Breakdown'}
                      >
                        {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </button>
                    </div>
                  </div>

                  {/* Allocation Logic Explainer Badge */}
                  {alloc.allocation_reason && (
                    <div style={{ fontSize: '0.73rem', color: 'var(--text-dim)', background: 'var(--surface)', padding: '0.3rem 0.6rem', borderRadius: '5px', border: '1px dashed var(--border)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span style={{ color: 'var(--accent)', fontWeight: 700 }}>🎯 Allocation Logic:</span>
                      <span>{alloc.allocation_reason}</span>
                    </div>
                  )}

                  {/* Impact Summary Pill Bar */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap', fontSize: '0.75rem' }}>
                    <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Downstream Blast Radius:</span>
                    <span className="badge" style={{ background: 'rgba(249, 115, 22, 0.15)', color: '#f97316', fontSize: '0.72rem', fontWeight: 700 }}>
                      ⚡ {alloc.direct_impact_count} Direct Callers Impacted {alloc.direct_impact_module_names?.length > 0 ? `(${alloc.direct_impact_module_names.slice(0, 2).join(', ')}${alloc.direct_impact_module_names.length > 2 ? '…' : ''})` : ''}
                    </span>
                    <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.15)', color: '#eab308', fontSize: '0.72rem', fontWeight: 700 }}>
                      🌊 {alloc.cascade_risk_count} Transitive Ripple Risk {alloc.cascade_risk_module_names?.length > 0 ? `(${alloc.cascade_risk_module_names.slice(0, 2).join(', ')}${alloc.cascade_risk_module_names.length > 2 ? '…' : ''})` : ''}
                    </span>
                  </div>

                  {/* Expandable Downstream Failure Breakdown */}
                  {isExpanded && (
                    <div
                      style={{
                        background: 'var(--surface)',
                        borderRadius: '6px',
                        border: '1px solid var(--border)',
                        padding: '0.75rem',
                        marginTop: '0.2rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.5rem',
                      }}
                    >
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                        💥 Exact Downstream Failures Caused Across Components:
                      </div>

                      {alloc.caused_issues?.map((ci, idx) => (
                        <div
                          key={idx}
                          style={{
                            background: 'var(--bg-dark-accent)',
                            padding: '0.45rem 0.65rem',
                            borderRadius: '5px',
                            border: '1px solid var(--border)',
                            fontSize: '0.75rem',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '0.2rem',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontWeight: 700, color: ci.impact_level === 'direct_impact' ? '#f97316' : '#eab308' }}>
                              {ci.impact_level === 'direct_impact' ? '⚡ 1st Degree Direct Caller' : '🌊 2nd Degree Ripple'}: {ci.target_module_name}
                            </span>
                            {ci.affected_defect_ids?.length > 0 && (
                              <span style={{ fontSize: '0.7rem', color: '#ef4444', fontWeight: 700 }}>
                                ⚠️ Compounding Defect #{ci.affected_defect_ids.join(', #')}
                              </span>
                            )}
                          </div>
                          <div style={{ color: 'var(--text)', lineHeight: 1.35 }}>
                            {ci.failure_description}
                          </div>
                        </div>
                      ))}

                      {/* Targeted Containment Advice */}
                      {alloc.containment_advice && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--accent)', marginTop: '0.2rem', fontWeight: 600 }}>
                          {alloc.containment_advice}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Main Interactive Split-Pane Visualizer ────────────────────────── */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 350px',
          gap: '1.25rem',
          alignItems: 'start',
        }}
        className="blast-visualizer-grid"
      >
        {/* Left Pane: Interactive SVG Network Graph Canvas */}
        <div
          style={{
            background: 'var(--surface)',
            borderRadius: 'var(--radius)',
            border: '1px solid var(--border)',
            padding: '1rem',
            boxShadow: 'var(--shadow-soft)',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          {/* Canvas Legend Ribbon */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '0.75rem',
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              flexWrap: 'wrap',
              gap: '0.5rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem', flexWrap: 'wrap' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ef4444', boxShadow: '0 0 6px #ef4444' }} /> Epicenter (Defects Origin)
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#f97316' }} /> Direct Impact (1st Degree)
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#eab308' }} /> Cascade Risk (2nd Degree)
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#10b981' }} /> Safe
              </span>
            </div>

            <span style={{ fontStyle: 'italic', fontSize: '0.7rem' }}>
              Click any module to inspect bidirectional cause & effect
            </span>
          </div>

          {/* SVG Dependency Graph */}
          <div style={{ position: 'relative', width: '100%', height: '520px', background: 'var(--bg-dark-accent)', borderRadius: '8px', border: '1px solid var(--border)', overflow: 'hidden' }}>
            <svg
              width="100%"
              height="100%"
              viewBox="0 0 860 520"
              style={{ width: '100%', height: '100%' }}
            >
              <defs>
                {/* Arrowhead Markers */}
                <marker id="arrow-normal" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--border)" />
                </marker>
                <marker id="arrow-active" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                  <path d="M 0 1 L 10 5 L 0 9 z" fill="#ef4444" />
                </marker>
                <marker id="arrow-cascade" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                  <path d="M 0 1 L 10 5 L 0 9 z" fill="#f97316" />
                </marker>

                {/* Radar Pulse Animation Styles */}
                <style>{`
                  @keyframes radarRing {
                    0% { r: 24; opacity: 0.8; }
                    100% { r: 52; opacity: 0; }
                  }
                  @keyframes dashFlow {
                    to { stroke-dashoffset: -20; }
                  }
                  .epicenter-ring-1 {
                    animation: radarRing 2s cubic-bezier(0.2, 0.8, 0.4, 1) infinite;
                  }
                  .epicenter-ring-2 {
                    animation: radarRing 2s cubic-bezier(0.2, 0.8, 0.4, 1) 0.7s infinite;
                  }
                  .active-impact-line {
                    stroke-dasharray: 6 4;
                    animation: dashFlow 1s linear infinite;
                  }
                `}</style>
              </defs>

              {/* 1. Dependency Edges (Links) */}
              {report.edges.map((edge, idx) => {
                const srcNodeIdx = report.nodes.findIndex((n) => n.id === edge.source);
                const tgtNodeIdx = report.nodes.findIndex((n) => n.id === edge.target);
                const srcPos = getNodePosition(edge.source, srcNodeIdx >= 0 ? srcNodeIdx : 0, report.nodes.length);
                const tgtPos = getNodePosition(edge.target, tgtNodeIdx >= 0 ? tgtNodeIdx : 1, report.nodes.length);
                const isHighlighted = activeEdges.some((ae) => ae.source === edge.source && ae.target === edge.target);

                const strokeColor = edge.is_active_impact_path
                  ? edge.severity_flow === 'critical'
                    ? '#ef4444'
                    : '#f97316'
                  : isHighlighted
                  ? 'var(--accent)'
                  : 'rgba(148, 163, 184, 0.25)';

                const strokeWidth = edge.is_active_impact_path ? 3 : isHighlighted ? 2.5 : 1.5;

                const midX = (srcPos.x + tgtPos.x) / 2;
                const midY = (srcPos.y + tgtPos.y) / 2;

                return (
                  <g key={`edge-${idx}`}>
                    <line
                      x1={srcPos.x}
                      y1={srcPos.y}
                      x2={tgtPos.x}
                      y2={tgtPos.y}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                      className={edge.is_active_impact_path ? 'active-impact-line' : ''}
                      markerEnd={edge.is_active_impact_path ? 'url(#arrow-active)' : 'url(#arrow-normal)'}
                    />

                    {/* Edge Label on active paths */}
                    {edge.is_active_impact_path && (
                      <g transform={`translate(${midX}, ${midY})`}>
                        <rect x="-35" y="-9" width="70" height="18" rx="4" fill="var(--surface)" stroke={strokeColor} strokeWidth="1" />
                        <text x="0" y="3.5" textAnchor="middle" fill="var(--text)" fontSize="8.5" fontWeight="700">
                          {edge.relation_type.replace('_', ' ')}
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}

              {/* 2. Module Nodes */}
              {report.nodes.map((node, nodeIdx) => {
                const pos = getNodePosition(node.id, nodeIdx, report.nodes.length);
                const isSelected = selectedNodeId === node.id;
                const isHovered = hoveredNodeId === node.id;
                const isEpicenter = node.blast_zone === 'epicenter';
                const isDirectImpact = node.blast_zone === 'direct_impact';
                const isCascadeRisk = node.blast_zone === 'cascade_risk';

                let nodeColor = '#10b981'; // safe
                if (isEpicenter) nodeColor = '#ef4444';
                else if (isDirectImpact) nodeColor = '#f97316';
                else if (isCascadeRisk) nodeColor = '#eab308';

                const IconComponent = MODULE_ICONS[node.id] || Layers;

                return (
                  <g
                    key={node.id}
                    transform={`translate(${pos.x}, ${pos.y})`}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelectedNodeId(node.id)}
                    onMouseEnter={() => setHoveredNodeId(node.id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                  >
                    {/* Epicenter Radiating Radar Wave Rings */}
                    {isEpicenter && (
                      <>
                        <circle cx="0" cy="0" r="32" fill="none" stroke="#ef4444" strokeWidth="2" className="epicenter-ring-1" />
                        <circle cx="0" cy="0" r="32" fill="none" stroke="#ef4444" strokeWidth="1.5" className="epicenter-ring-2" />
                      </>
                    )}

                    {/* Direct Impact Alert Ring */}
                    {isDirectImpact && (
                      <circle cx="0" cy="0" r="30" fill="none" stroke="#f97316" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.8" />
                    )}

                    {/* Node Outer Card Body */}
                    <rect
                      x="-70"
                      y="-28"
                      width="140"
                      height="56"
                      rx="10"
                      fill="var(--surface)"
                      stroke={isSelected || isHovered ? 'var(--accent)' : nodeColor}
                      strokeWidth={isSelected ? 2.5 : 1.5}
                      style={{
                        filter: isEpicenter
                          ? 'drop-shadow(0 0 12px rgba(239, 68, 68, 0.45))'
                          : isDirectImpact
                          ? 'drop-shadow(0 0 8px rgba(249, 115, 22, 0.35))'
                          : 'drop-shadow(0 2px 6px rgba(0,0,0,0.2))',
                        transition: 'all 0.2s ease',
                      }}
                    />

                    {/* Node Status Indicator Pill */}
                    <circle cx="-52" cy="-2" r="14" fill={`${nodeColor}20`} stroke={nodeColor} strokeWidth="1.5" />
                    <g transform="translate(-60, -10)">
                      <IconComponent size={16} color={nodeColor} />
                    </g>

                    {/* Module Title Text */}
                    <text x="-32" y="-4" fill="var(--text)" fontSize="10.5" fontWeight="700">
                      {node.name.length > 15 ? `${node.name.slice(0, 14)}…` : node.name}
                    </text>

                    {/* Category & Health Subtext */}
                    <text x="-32" y="10" fill="var(--text-muted)" fontSize="8.5">
                      {node.category} • {node.health_score}% HP
                    </text>

                    {/* Defect Count Badge */}
                    {node.open_defects_count > 0 && (
                      <g transform="translate(48, -28)">
                        <circle cx="10" cy="10" r="9" fill={node.critical_defects_count > 0 ? '#ef4444' : '#3b82f6'} />
                        <text x="10" y="13" textAnchor="middle" fill="#ffffff" fontSize="8" fontWeight="800">
                          {node.open_defects_count}
                        </text>
                      </g>
                    )}

                    {/* Epicenter LIVE Flasher */}
                    {isEpicenter && (
                      <g transform="translate(-25, -38)">
                        <rect x="0" y="0" width="50" height="14" rx="3" fill="#ef4444" />
                        <text x="25" y="10" textAnchor="middle" fill="#ffffff" fontSize="7.5" fontWeight="900" letterSpacing="0.5px">
                          EPICENTER
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        {/* Right Pane: Selected Module Inspection & Bidirectional Cause/Effect Shield */}
        {selectedNode && (
          <div
            style={{
              background: 'var(--surface)',
              borderRadius: 'var(--radius)',
              border: '1px solid var(--border)',
              padding: '1.25rem',
              boxShadow: 'var(--shadow-soft)',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
            }}
          >
            {/* Inspector Header */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
                  Module Inspection
                </span>
                <span
                  className="badge"
                  style={{
                    fontSize: '0.7rem',
                    textTransform: 'uppercase',
                    fontWeight: 700,
                    background:
                      selectedNode.blast_zone === 'epicenter'
                        ? 'rgba(239, 68, 68, 0.15)'
                        : selectedNode.blast_zone === 'direct_impact'
                        ? 'rgba(249, 115, 22, 0.15)'
                        : selectedNode.blast_zone === 'cascade_risk'
                        ? 'rgba(234, 179, 8, 0.15)'
                        : 'rgba(16, 185, 129, 0.15)',
                    color:
                      selectedNode.blast_zone === 'epicenter'
                        ? '#ef4444'
                        : selectedNode.blast_zone === 'direct_impact'
                        ? '#f97316'
                        : selectedNode.blast_zone === 'cascade_risk'
                        ? '#eab308'
                        : '#10b981',
                  }}
                >
                  {selectedNode.blast_zone.replace('_', ' ')}
                </span>
              </div>

              <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: 'var(--text)' }}>
                {selectedNode.name}
              </h3>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                Category: <strong>{selectedNode.category}</strong>
              </div>
            </div>

            {/* Health & Risk Stats */}
            <div style={{ background: 'var(--bg-dark-accent)', padding: '0.75rem 0.85rem', borderRadius: '8px', border: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>Health Integrity</span>
                <strong style={{ fontSize: '0.9rem', color: selectedNode.health_score > 70 ? 'var(--success)' : '#ef4444' }}>
                  {selectedNode.health_score}%
                </strong>
              </div>
              <div style={{ height: '5px', background: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${selectedNode.health_score}%`,
                    background: selectedNode.health_score > 70 ? 'var(--success)' : '#ef4444',
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.65rem' }}>
                <span>Active Bugs: <strong>{selectedNode.open_defects_count}</strong></span>
                <span>Critical: <strong style={{ color: selectedNode.critical_defects_count > 0 ? '#ef4444' : 'var(--text-muted)' }}>{selectedNode.critical_defects_count}</strong></span>
              </div>
            </div>

            {/* 1. Defects Originating in this Module (Causing Downstream Failures) */}
            {selectedNode.defect_ids?.length > 0 && (
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', color: '#ef4444', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <Flame size={13} /> Originating Defects ({selectedNode.defect_ids.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', maxHeight: '110px', overflowY: 'auto' }}>
                  {selectedNode.defect_ids.map((dId) => {
                    const issueMatch = issues.find((i) => i.id === dId);
                    return (
                      <div
                        key={dId}
                        onClick={() => issueMatch && onSelectIssue && onSelectIssue(issueMatch)}
                        style={{
                          background: 'var(--bg-dark-accent)',
                          padding: '0.4rem 0.6rem',
                          borderRadius: '6px',
                          border: '1px solid var(--border)',
                          fontSize: '0.75rem',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          cursor: issueMatch ? 'pointer' : 'default',
                        }}
                      >
                        <span style={{ fontWeight: 700, color: 'var(--accent)', fontFamily: 'monospace' }}>
                          #DEF-{dId}
                        </span>
                        <span style={{ color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '170px' }}>
                          {issueMatch?.title || 'Defect record'}
                        </span>
                        {issueMatch && (
                          <ExternalLink size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 2. Incoming Upstream Threats from Other Modules */}
            {incomingThreats.length > 0 && (
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', color: '#f97316', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <AlertTriangle size={13} /> Threatened by External Defects ({incomingThreats.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', maxHeight: '130px', overflowY: 'auto' }}>
                  {incomingThreats.map((threat, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: 'var(--bg-dark-accent)',
                        padding: '0.4rem 0.6rem',
                        borderRadius: '6px',
                        border: '1px solid var(--border)',
                        fontSize: '0.72rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.2rem',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 700, color: '#f97316' }}>
                          #DEF-{threat.defect_id} (in {threat.origin_module_name})
                        </span>
                        <span className="badge" style={{ fontSize: '0.65rem', padding: '0.1rem 0.35rem' }}>
                          {threat.impact_level === 'direct_impact' ? 'Direct' : 'Cascade'}
                        </span>
                      </div>
                      <div style={{ color: 'var(--text-muted)', lineHeight: 1.3 }}>
                        {threat.failure_description}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Assigned Developers */}
            {selectedNode.assigned_developers?.length > 0 && (
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Assigned Engineers
                </div>
                <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                  {selectedNode.assigned_developers.map((dev, i) => (
                    <span key={i} className="badge" style={{ background: 'var(--bg-dark-accent)', border: '1px solid var(--border)', fontSize: '0.75rem', color: 'var(--text)' }}>
                      👤 {dev}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* AI Recommended Containment Strategy */}
            <div style={{ background: 'rgba(2, 132, 199, 0.08)', border: '1px solid var(--accent)', borderRadius: '8px', padding: '0.85rem' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '0.35rem', marginBottom: '0.35rem' }}>
                <Shield size={14} /> AI Containment Strategy
              </div>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text)', lineHeight: 1.45 }}>
                {selectedNode.blast_zone === 'epicenter'
                  ? 'Isolate downstream callers with circuit breakers and queue critical background webhooks to dead-letter buffer.'
                  : selectedNode.blast_zone === 'direct_impact'
                  ? 'Apply defensive retry guards and fallback to cached read replicas while the epicenter defect is triaged.'
                  : 'Monitor error rates; nominal service flow unaffected at present.'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ── Bottom Executive Business Impact & Containment Actions ─────────── */}
      <div
        style={{
          background: 'var(--surface)',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--border)',
          padding: '1.25rem 1.5rem',
          boxShadow: 'var(--shadow-soft)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <ShieldAlert size={18} className="text-accent" />
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 800 }}>Executive Blast Impact & Containment Playbook</h3>
        </div>

        <p style={{ fontSize: '0.85rem', color: 'var(--text)', margin: '0 0 1rem', lineHeight: 1.5 }}>
          {report.estimated_user_impact}
        </p>

        {report.containment_strategies?.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.75rem' }}>
            {report.containment_strategies.map((strat, idx) => (
              <div
                key={idx}
                style={{
                  background: 'var(--bg-dark-accent)',
                  padding: '0.75rem 1rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border)',
                  fontSize: '0.8rem',
                  color: 'var(--text)',
                  lineHeight: 1.4,
                }}
              >
                {strat}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

