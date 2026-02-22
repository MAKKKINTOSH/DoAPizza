import { createContext, useContext, useState, useCallback } from 'react';

const AuthContext = createContext(null);

// Тестовый код для входа: 1234
// Любой номер телефона с кодом 1234 авторизуется как клиент

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
      
      // Проверяем только код - если код 1234, авторизуем как клиента
      if (code === '1234' && cleanPhone.length === 10) {
        const userData = { 
          id: Date.now(), // Временный ID
          phone: cleanPhone, 
          role: 'CLIENT' 
        };
        setUser(userData);
        localStorage.setItem('doapizza_user', JSON.stringify(userData));
        return { success: true, role: 'CLIENT' };
      }
      
      return { success: false, message: 'Неверный код. Используйте тестовый код: 1234' };
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
