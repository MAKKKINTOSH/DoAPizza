import { createContext, useContext, useState, useCallback } from 'react';
import { authApi } from '../../../shared/api';

const AuthContext = createContext(null);
const USER_KEY = 'doapizza_user';

function normalizePhone(phone) {
  let digits = String(phone || '').replace(/\D/g, '');
  if (digits.startsWith('8')) digits = '7' + digits.slice(1);
  if (!digits.startsWith('7')) digits = '7' + digits;
  return '+' + digits.slice(0, 11);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem(USER_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(false);

  const login = useCallback(async ({ phone, code }) => {
    setLoading(true);
    try {
      const phoneNumber = normalizePhone(phone);
      const result = await authApi.verifyCode(phoneNumber, code);
      if (result.success && result.user) {
        const u = {
          id: result.user.id,
          phone_number: result.user.phone_number,
          name: result.user.name || '',
          email: result.user.email || '',
          role: result.user.role || 'CLIENT',
          addresses: result.user.addresses || [],
        };
        setUser(u);
        localStorage.setItem(USER_KEY, JSON.stringify(u));
        return { success: true, role: u.role };
      }
      return { success: false, message: result.message || 'Ошибка входа' };
    } catch (err) {
      return { success: false, message: err.message || 'Ошибка входа' };
    } finally {
      setLoading(false);
    }
  }, []);

  const requestCode = useCallback(async (phone) => {
    setLoading(true);
    try {
      const phoneNumber = normalizePhone(phone);
      const result = await authApi.requestCode(phoneNumber);
      return result;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateUserName = useCallback((name) => {
    setUser((prev) => {
      if (!prev) return prev;
      const updated = { ...prev, name };
      localStorage.setItem(USER_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  const logout = useCallback(() => {
    authApi.logout();
    setUser(null);
    localStorage.removeItem(USER_KEY);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        role: user?.role || null,
        loading,
        login,
        requestCode,
        logout,
        updateUserName,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
