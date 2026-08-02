import { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';

export default function ThemeToggle() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('bugflow_theme') || 'dark';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('bugflow_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <button
      type="button"
      className="theme-toggle-btn"
      onClick={toggleTheme}
      title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
    >
      {theme === 'dark' ? (
        <>
          <Sun size={15} className="toggle-icon" />
          <span>Light Mode</span>
        </>
      ) : (
        <>
          <Moon size={15} className="toggle-icon" />
          <span>Dark Mode</span>
        </>
      )}
    </button>
  );
}
