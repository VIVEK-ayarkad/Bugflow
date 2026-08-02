import { useEffect, useState } from 'react';
import { X, BellCheck, CheckCheck } from 'lucide-react';
import { getNotifications, markAllNotificationsRead, markNotificationRead } from '../api';

export default function NotificationDrawer({ isOpen, onClose }) {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isOpen) {
      loadNotifications();
    }
  }, [isOpen]);

  async function loadNotifications() {
    try {
      const data = await getNotifications();
      setNotifications(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleMarkRead(id) {
    try {
      await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch {
      // ignore
    }
  }

  async function handleMarkAllRead() {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      // ignore
    }
  }

  if (!isOpen) return null;

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="notification-backdrop" onClick={onClose}>
      <div className="notification-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <h3>Notifications</h3>
            {unreadCount > 0 && <span className="badge badge-critical">{unreadCount} new</span>}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            {unreadCount > 0 && (
              <button className="btn-link" onClick={handleMarkAllRead} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                <CheckCheck size={14} /> Mark all read
              </button>
            )}
            <button className="btn-icon" onClick={onClose} title="Close">
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="drawer-body">
          {loading ? (
            <div className="loading-state">Loading notifications...</div>
          ) : notifications.length === 0 ? (
            <div className="empty-state">No notifications yet.</div>
          ) : (
            notifications.map((notif) => (
              <div
                key={notif.id}
                className={`notification-item ${notif.is_read ? 'read' : 'unread'}`}
                onClick={() => handleMarkRead(notif.id)}
              >
                <div className="notif-title">{notif.title}</div>
                <div className="notif-message">{notif.message}</div>
                <div className="notif-time">{new Date(notif.created_at).toLocaleString()}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
