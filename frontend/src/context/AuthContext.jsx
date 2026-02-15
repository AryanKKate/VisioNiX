import { createContext, useState, useCallback } from 'react';

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(false);

  const login = useCallback(async (email, password) => {
    setLoading(true);
    try {
      // Placeholder for API call
      // const response = await axios.post('/api/auth/login', { email, password });
      setUser({ email, id: Math.random() });
      setIsAuthenticated(true);
      localStorage.setItem('token', 'mock-token-' + Date.now());
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    } finally {
      setLoading(false);
    }
  }, []);

  const signup = useCallback(async (email, password, name) => {
    setLoading(true);
    try {
      // Placeholder for API call
      // const response = await axios.post('/api/auth/signup', { email, password, name });
      setUser({ email, name, id: Math.random() });
      setIsAuthenticated(true);
      localStorage.setItem('token', 'mock-token-' + Date.now());
      return { success: true };
    } catch (error) {
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
