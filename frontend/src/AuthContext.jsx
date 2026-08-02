import { createContext, useContext, useEffect, useState } from 'react';
import { getMe, getToken } from './api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    getMe()
      .then(setUser)
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false));
  }, []);

  const loginSuccess = (token, userData) => {
    localStorage.setItem('token', token);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  const hasRole = (...roles) => {
    if (!user) return false;
    if (user.role === 'admin') return true; // Admin has access to everything
    return roles.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        loginSuccess,
        logout,
        setUser,
        hasRole,
        isAdmin: user?.role === 'admin',
        isProjectManager: user?.role === 'project_manager' || user?.role === 'admin',
        isDeveloper: user?.role === 'developer' || user?.role === 'admin',
        isQA: user?.role === 'qa_tester' || user?.role === 'admin',
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
