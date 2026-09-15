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
  Search,
  X,
  FileDown,
  Pencil,
  Clock,
  CheckCircle,
  CheckCircle2,
  TrendingUp,
  Layers,
  BarChart3,
  AlertCircle,
  Activity,
} from 'lucide-react';
import {
  addProjectMember,
  aiSemanticSearch,
  createIssue,
  createProject,
  deleteIssue,
  deleteProject,
  downloadProjectPdf,
  getAllIssues,
  getDashboardStats,
  getProjectMembers,
  getProjects,
  getUsers,
  updateIssue,
  updateIssueStatus,
} from '../api';
import { useAuth } from '../AuthContext';
import AdminPanel from './AdminPanel';
import BugDetailModal from './BugDetailModal';
import IssueForm from './IssueForm';
import NotificationDrawer from './NotificationDrawer';
import ProfileModal from './ProfileModal';
import SprintManager from './SprintManager';
import ThemeToggle from './ThemeToggle';
import AIChatbot from './AIChatbot';
import BlastRadiusVisualizer from './BlastRadiusVisualizer';

function Badge({ value }) {
  const v = value || 'open';
  return (
    <span className={`badge badge-${v}`}>
      {v.replace('_', ' ')}
    </span>
  );
}

// ── SVG Charts & Analytics Components ─────────────────────────────────────────

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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', margin: 0 }}>
          <Flame size={16} color="#ef4444" /> Defects by Severity
        </h4>
        <span style={{ fontSize: '0.72rem', fontWeight: '700', padding: '0.15rem 0.5rem', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.12)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.25)' }}>
          {data.critical || 0} Critical
        </span>
      </div>

      <div className="severity-bar-container" style={{ margin: '0.85rem 0' }}>
        <div style={{ display: 'flex', height: '14px', borderRadius: '7px', overflow: 'hidden', background: 'var(--bg-dark-accent)', border: '1px solid var(--border)' }}>
          {items.map((item, i) => {
            const pct = (item.count / total) * 100;
            if (pct === 0) return null;
            return <div key={i} style={{ width: `${pct}%`, background: item.color }} title={`${item.label}: ${item.count} (${Math.round(pct)}%)`} />;
          })}
        </div>
      </div>

      <div className="chart-legend" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
        {items.map((item, i) => {
          const pct = Math.round((item.count / total) * 100);
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.82rem', padding: '0.2rem 0.35rem', background: 'var(--bg-dark-accent)', borderRadius: '4px', border: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span style={{ width: '9px', height: '9px', borderRadius: '50%', background: item.color }} />
                <span style={{ color: 'var(--text)' }}>{item.label}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>{pct}%</span>
                <strong>{item.count}</strong>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatusChart({ data = {} }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  const items = [
    { label: 'Open', count: data.open || 0, color: '#4f46e5' },
    { label: 'In Progress', count: data.in_progress || 0, color: '#0284c7' },
    { label: 'In Review', count: data.in_review || 0, color: '#7c3aed' },
    { label: 'Resolved', count: data.resolved || 0, color: '#059669' },
    { label: 'Closed', count: data.closed || 0, color: '#64748b' },
  ];

  return (
    <div className="chart-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', margin: 0 }}>
          <Zap size={16} color="var(--accent)" /> Defects by Status
        </h4>
        <span style={{ fontSize: '0.72rem', fontWeight: '700', padding: '0.15rem 0.5rem', borderRadius: '12px', background: 'var(--accent-light)', color: 'var(--accent)', border: '1px solid var(--border)' }}>
          {items.reduce((a, b) => a + b.count, 0)} Total
        </span>
      </div>

      <div style={{ margin: '0.85rem 0' }}>
        <div style={{ display: 'flex', height: '14px', borderRadius: '7px', overflow: 'hidden', background: 'var(--bg-dark-accent)', border: '1px solid var(--border)' }}>
          {items.map((item, i) => {
            const pct = (item.count / total) * 100;
            if (pct === 0) return null;
            return <div key={i} style={{ width: `${pct}%`, background: item.color }} title={`${item.label}: ${item.count} (${Math.round(pct)}%)`} />;
          })}
        </div>
      </div>

      <div className="chart-legend" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '0.45rem' }}>
        {items.map((item, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', padding: '0.25rem 0.4rem', background: 'var(--bg-dark-accent)', borderRadius: '4px', border: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: item.color }} />
              <span style={{ color: 'var(--text)', fontSize: '0.76rem' }}>{item.label}</span>
            </div>
            <strong>{item.count}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function CategoryChart({ data = [] }) {
  const categoryColors = [
    '#6366f1', // Indigo
    '#0ea5e9', // Sky
    '#10b981', // Emerald
    '#f59e0b', // Amber
    '#ec4899', // Pink
    '#8b5cf6', // Purple
    '#14b8a6', // Teal
    '#f97316', // Orange
    '#64748b', // Slate
  ];

  const total = data.reduce((acc, curr) => acc + curr.count, 0) || 1;

  return (
    <div className="chart-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', margin: 0 }}>
          <Layers size={16} color="var(--accent)" /> Defects by Category
        </h4>
        <span style={{ fontSize: '0.72rem', fontWeight: '700', padding: '0.15rem 0.5rem', borderRadius: '12px', background: 'var(--accent-light)', color: 'var(--accent)', border: '1px solid var(--border)' }}>
          {data.length} {data.length === 1 ? 'Category' : 'Categories'}
        </span>
      </div>

      {data.length === 0 ? (
        <p className="text-muted" style={{ fontSize: '0.85rem', margin: '1rem 0' }}>No categorized defects yet.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', marginTop: '0.5rem' }}>
          {/* Segmented multi-color bar */}
          <div style={{ display: 'flex', height: '14px', borderRadius: '7px', overflow: 'hidden', background: 'var(--bg-dark-accent)', border: '1px solid var(--border)' }}>
            {data.map((item, i) => {
              const pct = (item.count / total) * 100;
              if (pct === 0) return null;
              const color = categoryColors[i % categoryColors.length];
              return (
                <div
                  key={i}
                  style={{ width: `${pct}%`, background: color }}
                  title={`${item.category}: ${item.count} (${item.percentage}%)`}
                />
              );
            })}
          </div>

          {/* Category List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: '180px', overflowY: 'auto', paddingRight: '0.25rem' }}>
            {data.map((item, i) => {
              const color = categoryColors[i % categoryColors.length];
              return (
                <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.82rem', padding: '0.25rem 0.4rem', background: 'var(--bg-dark-accent)', borderRadius: '4px', border: '1px solid var(--border)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', minWidth: 0, flex: 1 }}>
                    <span style={{ width: '9px', height: '9px', borderRadius: '50%', background: color, flexShrink: 0 }} />
                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: 'var(--text)' }} title={item.category}>
                      {item.category}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexShrink: 0 }}>
                    <span style={{ fontSize: '0.74rem', color: 'var(--text-dim)', fontWeight: '600' }}>{item.percentage}%</span>
                    <strong style={{ minWidth: '20px', textAlign: 'right', color: 'var(--text)' }}>{item.count}</strong>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function DefectTrendsChart({ data = [] }) {
  const defaultMonths = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];
  const chartData = data.length > 0 ? data : defaultMonths.map((m) => ({ month: m, created_count: 0, resolved_count: 0 }));
  
  const createdCounts = chartData.map((d) => d.created_count ?? d.count ?? 0);
  const resolvedCounts = chartData.map((d) => d.resolved_count ?? 0);
  const maxVal = Math.max(...createdCounts, ...resolvedCounts, 4);
  const totalCreated = createdCounts.reduce((a, b) => a + b, 0);
  const totalResolved = resolvedCounts.reduce((a, b) => a + b, 0);

  const svgWidth = 440;
  const svgHeight = 175;
  const paddingLeft = 32;
  const paddingBottom = 25;
  const paddingTop = 25;
  const paddingRight = 15;

  const chartWidth = svgWidth - paddingLeft - paddingRight;
  const chartHeight = svgHeight - paddingTop - paddingBottom;
  const groupWidth = chartWidth / chartData.length;
  const barWidth = Math.min(14, groupWidth * 0.32);

  return (
    <div className="chart-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', margin: 0 }}>
          <TrendingUp size={16} color="var(--accent)" /> Defect Trends (Created vs Resolved)
        </h4>
        <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', fontSize: '0.74rem', fontWeight: '700' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', color: '#6366f1' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#6366f1' }} /> Created ({totalCreated})
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', color: '#10b981' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: '#10b981' }} /> Resolved ({totalResolved})
          </span>
        </div>
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
            const created = item.created_count ?? item.count ?? 0;
            const resolved = item.resolved_count ?? 0;
            
            const groupX = paddingLeft + i * groupWidth;
            const createdX = groupX + (groupWidth - barWidth * 2 - 4) / 2;
            const resolvedX = createdX + barWidth + 4;

            const cHeight = maxVal > 0 ? (created / maxVal) * chartHeight : 0;
            const cY = paddingTop + chartHeight - cHeight;

            const rHeight = maxVal > 0 ? (resolved / maxVal) * chartHeight : 0;
            const rY = paddingTop + chartHeight - rHeight;

            return (
              <g key={i} className="svg-bar-group" style={{ cursor: 'pointer' }}>
                {/* Created Bar */}
                {created > 0 && (
                  <text
                    x={createdX + barWidth / 2}
                    y={cY - 4}
                    textAnchor="middle"
                    fill="#6366f1"
                    fontSize="9"
                    fontWeight="700"
                  >
                    {created}
                  </text>
                )}
                <rect
                  x={createdX}
                  y={Math.min(cY, paddingTop + chartHeight - 2)}
                  width={barWidth}
                  height={Math.max(cHeight, 2)}
                  rx="3"
                  ry="3"
                  fill="#6366f1"
                  title={`Created: ${created}`}
                />

                {/* Resolved Bar */}
                {resolved > 0 && (
                  <text
                    x={resolvedX + barWidth / 2}
                    y={rY - 4}
                    textAnchor="middle"
                    fill="#10b981"
                    fontSize="9"
                    fontWeight="700"
                  >
                    {resolved}
                  </text>
                )}
                <rect
                  x={resolvedX}
                  y={Math.min(rY, paddingTop + chartHeight - 2)}
                  width={barWidth}
                  height={Math.max(rHeight, 2)}
                  rx="3"
                  ry="3"
                  fill="#10b981"
                  title={`Resolved: ${resolved}`}
                />

                {/* X-Axis Month Label */}
                <text
                  x={groupX + groupWidth / 2}
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
        </svg>
      </div>
    </div>
  );
}

function WorkloadChart({ data = [] }) {
  const maxCount = Math.max(...data.map((d) => d.count), 5);

  return (
    <div className="chart-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', margin: 0 }}>
          <Users size={16} color="var(--accent)" /> Developer Workload
        </h4>
        <span style={{ fontSize: '0.72rem', fontWeight: '700', padding: '0.15rem 0.5rem', borderRadius: '12px', background: 'var(--accent-light)', color: 'var(--accent)', border: '1px solid var(--border)' }}>
          {data.length} assigned
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', marginTop: '0.4rem', maxHeight: '200px', overflowY: 'auto', paddingRight: '0.25rem' }}>
        {data.length === 0 ? (
          <p className="text-muted" style={{ fontSize: '0.85rem' }}>No assigned workload.</p>
        ) : (
          data.map((item, i) => {
            const activeCount = item.active_count ?? (item.open_count + item.in_progress_count + item.in_review_count);
            const resolvedCount = item.resolved_count ?? 0;
            const totalCount = item.count || (activeCount + resolvedCount);
            const activePct = totalCount > 0 ? (activeCount / totalCount) * 100 : 0;
            const resolvedPct = totalCount > 0 ? (resolvedCount / totalCount) * 100 : 0;

            return (
              <div key={i} style={{ padding: '0.5rem 0.65rem', background: 'var(--bg-dark-accent)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.82rem', marginBottom: '0.35rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <div style={{ width: '22px', height: '22px', borderRadius: '50%', background: 'var(--accent-light)', color: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: '800' }}>
                      {item.developer?.[0]?.toUpperCase() || '?'}
                    </div>
                    <span style={{ fontWeight: '700', color: 'var(--text)' }}>{item.developer}</span>
                    {item.critical_count > 0 && (
                      <span style={{ fontSize: '0.68rem', padding: '0.1rem 0.4rem', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', fontWeight: '700' }}>
                        {item.critical_count} critical
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    <strong style={{ color: 'var(--accent)' }}>{activeCount}</strong> active / <strong style={{ color: '#10b981' }}>{resolvedCount}</strong> done
                  </div>
                </div>

                {/* Progress bar with active vs resolved */}
                <div style={{ height: '7px', background: 'var(--surface)', borderRadius: '4px', overflow: 'hidden', border: '1px solid var(--border)', display: 'flex' }}>
                  {activeCount > 0 && (
                    <div style={{ width: `${activePct}%`, background: '#6366f1' }} title={`Active: ${activeCount}`} />
                  )}
                  {resolvedCount > 0 && (
                    <div style={{ width: `${resolvedPct}%`, background: '#10b981' }} title={`Resolved: ${resolvedCount}`} />
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

function ResolutionTimeChart({ summary = {}, data = {} }) {
  const avgHours = summary.avg_resolution_time_hours;
  const avgDays = summary.avg_resolution_time_days;
  const resolutionRate = summary.resolution_rate ?? 0;
  const resolvedCount = summary.total_resolved_and_closed || 0;
  const totalCount = summary.total_bugs || 0;

  const severityOrder = [
    { key: 'critical', label: 'Critical', color: '#ef4444' },
    { key: 'high', label: 'High', color: '#f97316' },
    { key: 'medium', label: 'Medium', color: '#eab308' },
    { key: 'low', label: 'Low', color: '#3b82f6' },
  ];

  const hasOverallData = avgHours !== null && avgHours !== undefined;
  const daysDisplay = avgDays !== null && avgDays !== undefined
    ? `${avgDays} days`
    : hasOverallData
    ? `${(avgHours / 24).toFixed(1)} days`
    : 'N/A';
  const hoursDisplay = hasOverallData ? `${avgHours} hrs` : 'N/A';

  return (
    <div className="chart-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <h4 style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', margin: 0 }}>
          <Clock size={16} color="var(--accent)" /> Average Resolution Time (MTTR)
        </h4>
        <span style={{ fontSize: '0.72rem', fontWeight: '700', padding: '0.15rem 0.5rem', borderRadius: '12px', background: 'rgba(16, 185, 129, 0.12)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.25)' }}>
          {resolutionRate}% Resolved
        </span>
      </div>

      {/* Main Stat Highlight - Displayed in both Days and Hours */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '0.5rem 0 0.85rem 0', padding: '0.75rem 0.9rem', background: 'var(--bg-dark-accent)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)', flexWrap: 'wrap', gap: '0.6rem' }}>
        <div>
          {hasOverallData ? (
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.55rem', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '1.55rem', fontWeight: '800', fontFamily: 'var(--display)', color: 'var(--accent)' }}>
                {daysDisplay}
              </span>
              <span style={{ fontSize: '1rem', fontWeight: '700', color: 'var(--text)', background: 'rgba(99, 102, 241, 0.12)', padding: '0.15rem 0.55rem', borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.25)' }}>
                {hoursDisplay}
              </span>
            </div>
          ) : (
            <span style={{ fontSize: '1.55rem', fontWeight: '800', fontFamily: 'var(--display)', color: 'var(--text-muted)' }}>
              N/A
            </span>
          )}
          <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', fontWeight: '600', marginTop: '0.2rem' }}>
            Overall MTTR (Mean Time To Resolution in Days &amp; Hours)
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--text)' }}>
            {resolvedCount} / {totalCount}
          </span>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Resolved Defects</div>
        </div>
      </div>

      {/* Breakdown by Severity - Displayed in both Days and Hours */}
      <div style={{ fontSize: '0.74rem', fontWeight: '700', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.45rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>MTTR by Severity Tier</span>
        <span style={{ fontSize: '0.68rem', textTransform: 'none', color: 'var(--text-muted)' }}>Days &amp; Hours</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.45rem' }}>
        {severityOrder.map((s) => {
          const item = data[s.key] || { count: 0, avg_hours: null, avg_days: null, formatted: 'N/A' };
          const hasItemData = item.count > 0 && item.avg_hours !== null && item.avg_hours !== undefined;
          const sevDays = item.avg_days !== null && item.avg_days !== undefined ? item.avg_days : hasItemData ? +(item.avg_hours / 24).toFixed(1) : null;
          return (
            <div key={s.key} style={{ padding: '0.45rem 0.6rem', background: 'var(--bg-dark-accent)', borderRadius: '6px', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.74rem', fontWeight: '700', color: s.color }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: s.color }} />
                  {s.label}
                </span>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>({item.count})</span>
              </div>
              {hasItemData ? (
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.35rem', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.88rem', fontWeight: '800', color: 'var(--text)' }}>
                    {sevDays} d
                  </span>
                  <span style={{ fontSize: '0.74rem', fontWeight: '600', color: 'var(--text-dim)' }}>
                    ({item.avg_hours} hrs)
                  </span>
                </div>
              ) : (
                <div style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)' }}>
                  N/A
                </div>
              )}
            </div>
          );
        })}
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
  const [semanticMode, setSemanticMode] = useState(true);

  // Modals
  const [showNewProject, setShowNewProject] = useState(false);
  const [showNewIssue, setShowNewIssue] = useState(false);
  const [editingIssue, setEditingIssue] = useState(null);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [showMembersModal, setShowMembersModal] = useState(false);
  const [projectMembers, setProjectMembers] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [selectedAddUserId, setSelectedAddUserId] = useState('');
  const [notifOpen, setNotifOpen] = useState(false);
  const [aiChatContext, setAiChatContext] = useState(null);

  function handleOpenAIChat(ctx = null) {
    setAiChatContext(ctx);
  }

  // Form State
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');
  const [error, setError] = useState('');
  const [downloadingProjectPdf, setDownloadingProjectPdf] = useState(false);

  async function handleUpdateIssueSubmit(payload) {
    if (!editingIssue) return;
    try {
      await updateIssue(editingIssue.id, payload);
      setEditingIssue(null);
      loadIssuesAndStats();
    } catch (err) {
      alert(`Failed to update bug: ${err.message}`);
    }
  }

  async function handleDownloadProjectPdf() {
    if (!selectedProject) {
      alert('Please select a project first!');
      return;
    }
    setDownloadingProjectPdf(true);
    try {
      await downloadProjectPdf(selectedProject.id, selectedProject.name);
    } catch (err) {
      alert(`Failed to download project PDF: ${err.message}`);
    } finally {
      setDownloadingProjectPdf(false);
    }
  }

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    loadIssuesAndStats();
  }, [selectedProject, navTab, statusFilter, severityFilter, priorityFilter, searchQuery, semanticMode]);

  async function loadProjects() {
    try {
      let data = await getProjects();
      if (!data || data.length === 0) {
        try {
          const defaultProj = await createProject({ name: 'BugFlow Workspace', description: 'Default project for software defect tracking.' });
          data = [defaultProj];
        } catch {
          // ignore
        }
      }
      setProjects(data || []);
      if (data && data.length && !selectedProject) setSelectedProject(data[0]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadIssuesAndStats() {
    try {
      const pId = selectedProject ? selectedProject.id : null;
      const statsData = await getDashboardStats(pId);
      setStats(statsData);

      if (searchQuery.trim() && semanticMode && !searchQuery.trim().startsWith('#')) {
        const semRes = await aiSemanticSearch(searchQuery.trim(), pId, 0.30);
        let semList = semRes.results || [];
        if (statusFilter !== 'all') {
          semList = semList.filter((i) => (i.status || '').toLowerCase() === statusFilter.toLowerCase());
        }
        if (severityFilter !== 'all') {
          semList = semList.filter((i) => (i.severity || '').toLowerCase() === severityFilter.toLowerCase());
        }
        if (priorityFilter !== 'all') {
          semList = semList.filter((i) => (i.priority || '').toLowerCase() === priorityFilter.toLowerCase());
        }
        setIssues(semList);
      } else {
        const issuesData = await getAllIssues({
          project_id: pId,
          search: searchQuery,
          status: statusFilter,
          severity: severityFilter,
          priority: priorityFilter,
          my_bugs_only: navTab === 'my_bugs',
        });
        setIssues(issuesData);
      }
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
    let targetProjectId = selectedProject?.id;
    if (!targetProjectId) {
      if (projects && projects.length > 0) {
        targetProjectId = projects[0].id;
        setSelectedProject(projects[0]);
      } else {
        const newProj = await createProject({ name: 'BugFlow Workspace', description: 'Primary defect tracking workspace' });
        setProjects([newProj]);
        setSelectedProject(newProj);
        targetProjectId = newProj.id;
      }
    }
    await createIssue(targetProjectId, payload);
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
          <div className="brand-icon" style={{ background: 'transparent', boxShadow: 'none' }}>
            <img src="/logo.png" alt="BugFlow Logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
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
          <button className={`nav-item ${navTab === 'blast_radius' ? 'active' : ''}`} onClick={() => setNavTab('blast_radius')}>
            <Flame size={16} color="var(--accent)" /> Blast Radius Map
          </button>
          <button className={`nav-item ${navTab === 'projects' ? 'active' : ''}`} onClick={() => setNavTab('projects')}>
            <FolderKanban size={16} /> Projects & Team
          </button>
          <button className={`nav-item ${navTab === 'chatbot' ? 'active' : ''}`} onClick={() => setNavTab('chatbot')}>
            <Bot size={16} /> AI Mentor & Chatbot
          </button>

          {isAdmin && (
            <button className={`nav-item ${navTab === 'admin' ? 'active' : ''}`} onClick={() => setNavTab('admin')}>
              <ShieldCheck size={16} /> Admin Panel
            </button>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="user-info" onClick={() => setShowProfileModal(true)} style={{ cursor: 'pointer' }} title="Click to view & edit profile">
            <div className="avatar">{user?.username?.[0]?.toUpperCase()}</div>
            <div className="user-details">
              <span className="username">{user?.username}</span>
              <span className="user-role">{user?.role}</span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.2rem' }}>
            <button className="btn-icon" onClick={() => setShowProfileModal(true)} title="Edit Profile">
              <User size={15} />
            </button>
            <button className="btn-logout" onClick={logout} title="Sign Out">
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Top Navigation Bar */}
        <header className="top-navbar">
          <div className="top-navbar-actions">
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setNavTab('chatbot')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
              title="Open AI Mentor & Bug Q&A"
            >
              <Bot size={14} color="var(--accent)" /> AI Mentor
            </button>

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
              {/* Dashboard Banner Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                <div>
                  <h2 style={{ fontSize: '1.4rem', fontWeight: '800', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--display)' }}>
                    <BarChart3 size={22} color="var(--accent)" /> QA Analytics & Defect Dashboard
                  </h2>
                  <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                    Project: <strong style={{ color: 'var(--text)' }}>{selectedProject ? selectedProject.name : 'All Projects'}</strong> • Real-time defect intelligence, resolution velocity, and engineer workloads.
                  </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={handleDownloadProjectPdf}
                    disabled={downloadingProjectPdf || !selectedProject}
                    title="Download Project QA Defect Report as PDF"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                  >
                    <FileDown size={14} />
                    {downloadingProjectPdf ? 'Generating PDF...' : 'Download Project PDF'}
                  </button>
                </div>
              </div>

              {/* 8 Metric Summary KPI Cards */}
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-card-header">
                    <span className="stat-label">Total Defects</span>
                    <Bug size={16} color="var(--accent)" />
                  </div>
                  <span className="stat-number">{stats.summary.total_bugs}</span>
                  <span className="stat-subtext">All logged defects</span>
                </div>

                <div className="stat-card">
                  <div className="stat-card-header">
                    <span className="stat-label">Open Defects</span>
                    <AlertCircle size={16} color="#3b82f6" />
                  </div>
                  <span className="stat-number" style={{ color: '#3b82f6' }}>{stats.summary.open_bugs}</span>
                  <span className="stat-subtext">Awaiting triage</span>
                </div>

                <div className="stat-card">
                  <div className="stat-card-header">
                    <span className="stat-label">In Progress / Review</span>
                    <Activity size={16} color="#0284c7" />
                  </div>
                  <span className="stat-number" style={{ color: '#0284c7' }}>
                    {(stats.summary.in_progress_bugs || 0) + (stats.summary.in_review_bugs || 0)}
                  </span>
                  <span className="stat-subtext">Active development</span>
                </div>

                <div className="stat-card">
                  <div className="stat-card-header">
                    <span className="stat-label">Resolved Defects</span>
                    <CheckCircle2 size={16} color="#10b981" />
                  </div>
                  <span className="stat-number" style={{ color: '#10b981' }}>{stats.summary.resolved_bugs}</span>
                  <span className="stat-subtext">Fixed by developers</span>
                </div>

                <div className="stat-card">
                  <div className="stat-card-header">
                    <span className="stat-label">Closed Defects</span>
                    <CheckCircle size={16} color="#64748b" />
                  </div>
                  <span className="stat-number" style={{ color: '#64748b' }}>{stats.summary.closed_bugs}</span>
                  <span className="stat-subtext">QA verified & closed</span>
                </div>

                <div className="stat-card">
                  <div className="stat-card-header">
                    <span className="stat-label">Avg Resolution Time (MTTR)</span>
                    <Clock size={16} color="var(--accent)" />
                  </div>
                  {stats.summary.avg_resolution_time_hours !== null && stats.summary.avg_resolution_time_hours !== undefined ? (
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem', flexWrap: 'wrap' }}>
                      <span className="stat-number" style={{ color: 'var(--accent)', fontSize: '1.35rem' }}>
                        {stats.summary.avg_resolution_time_days !== null && stats.summary.avg_resolution_time_days !== undefined
                          ? `${stats.summary.avg_resolution_time_days}d`
                          : `${(stats.summary.avg_resolution_time_hours / 24).toFixed(1)}d`}
                      </span>
                      <span style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--text-dim)', background: 'var(--bg-dark-accent)', padding: '0.1rem 0.4rem', borderRadius: '4px', border: '1px solid var(--border)' }}>
                        {stats.summary.avg_resolution_time_hours} hrs
                      </span>
                    </div>
                  ) : (
                    <span className="stat-number" style={{ color: 'var(--accent)', fontSize: '1.35rem' }}>
                      {stats.summary.avg_resolution_time_formatted || 'N/A'}
                    </span>
                  )}
                  <span className="stat-subtext">{stats.summary.resolution_rate}% resolution rate</span>
                </div>

                <div className="stat-card">
                  <div className="stat-card-header">
                    <span className="stat-label">Critical Defects</span>
                    <Flame size={16} color="#ef4444" />
                  </div>
                  <span className="stat-number" style={{ color: '#ef4444' }}>
                    {stats.summary.critical_bugs}
                  </span>
                  <span className="stat-subtext">Requires immediate fix</span>
                </div>

                <div className="stat-card">
                  <div className="stat-card-header">
                    <span className="stat-label">Assigned to Me</span>
                    <Target size={16} color="var(--accent)" />
                  </div>
                  <span className="stat-number" style={{ color: 'var(--accent)' }}>
                    {stats.summary.assigned_bugs}
                  </span>
                  <span className="stat-subtext">My active queue</span>
                </div>
              </div>

              {/* 6 Analytics Chart Grid */}
              <div className="charts-grid">
                <DefectTrendsChart data={stats.charts.monthly_reports} />
                <CategoryChart data={stats.charts.by_category} />
                <SeverityChart data={stats.charts.by_severity} />
                <StatusChart data={stats.charts.by_status} />
                <WorkloadChart data={stats.charts.developer_workload} />
                <ResolutionTimeChart summary={stats.summary} data={stats.charts.resolution_by_severity} />
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
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, maxWidth: '440px' }}>
                  <div style={{ position: 'relative', width: '100%', display: 'flex', alignItems: 'center' }}>
                    <Search size={15} style={{ position: 'absolute', left: '0.75rem', color: semanticMode ? 'var(--accent)' : 'var(--text-dim)', pointerEvents: 'none' }} />
                    <input
                      type="text"
                      placeholder={semanticMode ? "✨ Semantic Search: e.g. Payment fails after clicking submit..." : "Exact Search by ID (#5), title, or desc..."}
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      style={{
                        paddingLeft: '2.2rem',
                        paddingRight: searchQuery ? '2rem' : '0.75rem',
                        height: '36px',
                        fontSize: '0.85rem',
                        width: '100%',
                        borderRadius: 'var(--radius-sm)',
                        borderColor: semanticMode && searchQuery ? 'var(--accent)' : 'var(--border)'
                      }}
                    />
                    {searchQuery && (
                      <button
                        type="button"
                        onClick={() => setSearchQuery('')}
                        style={{
                          position: 'absolute',
                          right: '0.6rem',
                          background: 'transparent',
                          border: 'none',
                          color: 'var(--text-dim)',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          padding: 0,
                        }}
                        title="Clear search"
                      >
                        <X size={14} />
                      </button>
                    )}
                  </div>

                  <button
                    type="button"
                    className={`btn-sm ${semanticMode ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setSemanticMode(!semanticMode)}
                    title="Toggle AI Semantic Search vs Keyword Search"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      whiteSpace: 'nowrap',
                      fontSize: '0.78rem',
                      padding: '0.45rem 0.65rem'
                    }}
                  >
                    <Sparkles size={13} /> {semanticMode ? 'Semantic' : 'Keyword'}
                  </button>
                </div>

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
                    className="btn btn-secondary btn-sm"
                    onClick={handleDownloadProjectPdf}
                    disabled={downloadingProjectPdf || !selectedProject}
                    title="Download Project Defect Summary as PDF"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                  >
                    <FileDown size={14} />
                    {downloadingProjectPdf ? 'Generating PDF...' : 'Download Project PDF'}
                  </button>
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
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
                                  <strong>{issue.title}</strong>
                                  {issue.similarity_score && (
                                    <span className="badge" style={{ fontSize: '0.68rem', padding: '0.1rem 0.45rem', background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', borderColor: '#a855f7' }}>
                                      ✨ {issue.similarity_score}% Match
                                    </span>
                                  )}
                                  {issue.category && (
                                    <span className="badge" style={{ fontSize: '0.68rem', padding: '0.1rem 0.45rem', background: 'var(--accent-light)', color: 'var(--accent)', borderColor: 'var(--border)' }}>
                                      {issue.category}
                                    </span>
                                  )}
                                  {issue.module && (
                                    <span className="badge" style={{ fontSize: '0.68rem', padding: '0.1rem 0.45rem', background: 'var(--bg-dark-accent)', color: 'var(--text-muted)' }}>
                                      {issue.module}
                                    </span>
                                  )}
                                </div>
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
                            <td>{issue.assigned_developer?.username || <span style={{ color: 'var(--text-dim)' }}>Unassigned</span>}</td>
                            <td>{issue.reporter?.username || 'System'}</td>
                            <td style={{ whiteSpace: 'nowrap', fontSize: '0.8rem', color: 'var(--text-dim)' }}>
                              {new Date(issue.created_at).toLocaleDateString()}
                            </td>
                            <td onClick={(e) => e.stopPropagation()}>
                              <div style={{ display: 'flex', gap: '0.35rem' }}>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  onClick={() => setEditingIssue(issue)}
                                  title="Edit Bug"
                                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}
                                >
                                  <Pencil size={13} /> Edit
                                </button>
                                <button
                                  className="btn btn-secondary btn-sm danger"
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
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.8rem', gap: '0.3rem', flexWrap: 'wrap' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexWrap: 'wrap' }}>
                                  <span className="bug-id-tag">#{issue.id}</span>
                                  {issue.similarity_score && (
                                    <span className="badge" style={{ fontSize: '0.65rem', padding: '0.05rem 0.35rem', background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', borderColor: '#a855f7' }}>
                                      ✨ {issue.similarity_score}%
                                    </span>
                                  )}
                                  {issue.category && (
                                    <span className="badge" style={{ fontSize: '0.65rem', padding: '0.05rem 0.35rem', background: 'var(--accent-light)', color: 'var(--accent)' }}>
                                      {issue.category}
                                    </span>
                                  )}
                                </div>
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
                                    className="btn-icon-xs"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setEditingIssue(issue);
                                    }}
                                    title="Edit Bug"
                                  >
                                    <Pencil size={12} />
                                  </button>
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
            <SprintManager
              projectId={selectedProject?.id}
              project={selectedProject}
              issues={issues}
              onSelectIssue={(issue) => setSelectedIssue(issue)}
              onRefresh={loadIssuesAndStats}
            />
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

          {/* TAB 5: BLAST RADIUS & ARCHITECTURE MAP */}
          {navTab === 'blast_radius' && (
            <BlastRadiusVisualizer
              projectId={selectedProject?.id}
              issues={issues}
              onSelectIssue={(issue) => setSelectedIssue(issue)}
            />
          )}

          {/* TAB 6: AI MENTOR & CHATBOT WORKSTATION */}
          {navTab === 'chatbot' && (
            <div style={{ height: 'calc(100vh - 120px)' }}>
              <AIChatbot mode="fullscreen" initialContext={aiChatContext} />
            </div>
          )}

          {/* TAB 7: ADMIN PANEL */}
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
              onOpenAIChat={handleOpenAIChat}
            />
          </div>
        </div>
      )}

      {editingIssue && (
        <div className="modal-overlay" onClick={() => setEditingIssue(null)}>
          <div className="modal modal-lg" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Pencil size={20} color="var(--accent)" /> Edit Defect #{editingIssue.id}: {editingIssue.title}
              </h2>
              <button className="btn-icon" onClick={() => setEditingIssue(null)}>
                <X size={18} />
              </button>
            </div>
            <IssueForm
              initial={editingIssue}
              projectId={editingIssue.project_id || selectedProject?.id}
              onSubmit={handleUpdateIssueSubmit}
              onCancel={() => setEditingIssue(null)}
              submitLabel="Save Changes"
              onOpenAIChat={handleOpenAIChat}
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
          onOpenAIChat={handleOpenAIChat}
        />
      )}

      {showProfileModal && (
        <ProfileModal onClose={() => setShowProfileModal(false)} />
      )}

      <NotificationDrawer isOpen={notifOpen} onClose={() => setNotifOpen(false)} />

      {/* Global Floating AI Mentor Widget */}
      {navTab !== 'chatbot' && (
        <AIChatbot mode="widget" initialContext={aiChatContext} />
      )}
    </div>
  );
}
