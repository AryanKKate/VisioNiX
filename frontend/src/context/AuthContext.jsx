import { createContext, useEffect, useState, useCallback } from 'react';

export const AuthContext = createContext();

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(false);

  const hydrateSession = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      return;
    }

    try {
      const response = await fetch(`${apiBaseUrl}/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Session expired');
      }

      const data = await response.json();
      setUser(data.user || null);
      setIsAuthenticated(Boolean(data.user));
    } catch {
      localStorage.removeItem('token');
      setUser(null);
      setIsAuthenticated(false);
    }
  }, []);

  useEffect(() => {
    hydrateSession();
  }, [hydrateSession]);

  const login = useCallback(async (email, password) => {
    setLoading(true);
    try {
      const response = await fetch(`${apiBaseUrl}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Login failed');
      }

      const accessToken = data.session?.access_token;
      if (!accessToken) {
        throw new Error('No access token returned from backend');
      }

      localStorage.setItem('token', accessToken);
      setUser(data.user || null);
      setIsAuthenticated(Boolean(data.user));
      return { success: true };
    } catch (error) {
      setUser(null);
      setIsAuthenticated(false);
      return { success: false, error: error.message };
    } finally {
      setLoading(false);
    }
  }, []);

  const signup = useCallback(async (email, password) => {
    setLoading(true);
    try {
      const response = await fetch(`${apiBaseUrl}/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'Signup failed');
      }

      const accessToken = data.session?.access_token;
      if (!accessToken) {
        throw new Error('Sign up successful. Please verify your email, then sign in.');
      }

      localStorage.setItem('token', accessToken);
      setUser(data.user || null);
      setIsAuthenticated(Boolean(data.user));
      return { success: true };
    } catch (error) {
      setUser(null);
      setIsAuthenticated(false);
      return { success: false, error: error.message };
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('token');
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
