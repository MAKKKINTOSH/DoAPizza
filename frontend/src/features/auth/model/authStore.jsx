import { createContext, useContext, useState, useCallback } from 'react';

const AuthContext = createContext(null);

// Мок-пользователи.
// Код для входа (одноразовый код в демо): 12345
// Номера (можно вводить как 7900 000 00 01 / 7900 000 00 02 и т.п., мы берём последние 10 цифр):
// - Клиент: 7900 000 00 01  → 9000000001
// - Курьер: 7900 000 00 02  → 9000000002
const MOCK_USERS = [
  { id: 1, phone: '9001234567', code: '12345', role: 'ADMIN' },
  { id: 2, phone: '9000000001', code: '12345', role: 'CLIENT' },
  { id: 3, phone: '9000000002', code: '12345', role: 'COURIER' },
];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('doapizza_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(false);

  const login = useCallback(async ({ phone, code }) => {
    setLoading(true);
    try {
      const cleanPhone = String(phone).replace(/\D/g, '').slice(-10);
      const found = MOCK_USERS.find(
        (u) => u.phone === cleanPhone && u.code === code
      );
      if (found) {
        const userData = { id: found.id, phone: found.phone, role: found.role };
        setUser(userData);
        localStorage.setItem('doapizza_user', JSON.stringify(userData));
        return { success: true, role: found.role };
      }
      return { success: false, message: 'Неверный телефон или код' };
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
