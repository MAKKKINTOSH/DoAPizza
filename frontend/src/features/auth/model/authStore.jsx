import { createContext, useContext, useState, useCallback } from 'react';

const AuthContext = createContext(null);

// Мок: админ 9001234567 / 12345
const MOCK_USERS = [
  { id: 1, phone: '9001234567', password: '12345', role: 'ADMIN' },
  { id: 2, phone: '9001112233', password: '12345', role: 'CLIENT' },
];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('doapizza_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(false);

  const login = useCallback(async ({ phone, password }) => {
    setLoading(true);
    try {
      const cleanPhone = String(phone).replace(/\D/g, '').slice(-10);
      const found = MOCK_USERS.find(
        (u) => u.phone === cleanPhone && u.password === password
      );
      if (found) {
        const userData = { id: found.id, phone: found.phone, role: found.role };
        setUser(userData);
        localStorage.setItem('doapizza_user', JSON.stringify(userData));
        return { success: true, role: found.role };
      }
      return { success: false, message: 'Неверный телефон или пароль' };
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('doapizza_user');
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        role: user?.role || null,
        loading,
        login,
        logout,
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
