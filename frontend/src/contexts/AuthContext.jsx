/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useCallback, useEffect } from 'react';

const AuthContext = createContext(null);

const AUTH_KEYS = {
  TOKEN: 'auth_token',
  REFRESH_TOKEN: 'auth_refresh_token',
  USER: 'auth_user',
  IS_AUTHENTICATED: 'auth_is_authenticated',
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem(AUTH_KEYS.USER);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [isAuthenticated, setIsAuthenticated] = useState(
    () =>
      localStorage.getItem(AUTH_KEYS.IS_AUTHENTICATED) === 'true' &&
      Boolean(localStorage.getItem(AUTH_KEYS.TOKEN)),
  );

  const login = useCallback((userData, accessToken, refreshToken) => {
    try {
      localStorage.setItem(AUTH_KEYS.TOKEN, accessToken);
      localStorage.setItem(AUTH_KEYS.REFRESH_TOKEN, refreshToken);
      localStorage.setItem(AUTH_KEYS.USER, JSON.stringify(userData));
      localStorage.setItem(AUTH_KEYS.IS_AUTHENTICATED, 'true');
    } catch {
      /* noop */
    }
    setUser(userData);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    try {
      Object.values(AUTH_KEYS).forEach((k) => localStorage.removeItem(k));
    } catch {
      /* noop */
    }
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  useEffect(() => {
    const onForcedLogout = () => logout();
    window.addEventListener('auth:logout', onForcedLogout);
    return () => window.removeEventListener('auth:logout', onForcedLogout);
  }, [logout]);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};

export default AuthContext;
