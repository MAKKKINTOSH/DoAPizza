import { createContext, useContext, useState, useCallback } from 'react';

const AuthContext = createContext(null);

// Тестовый код для входа: 1234
// Любой номер телефона с кодом 1234 авторизуется как клиент

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('doapizza_user');
    if (saved) {
      const userData = JSON.parse(saved);
      // Восстанавливаем имя из отдельного хранилища, если его нет в userData
      if (!userData.name) {
        const savedName = localStorage.getItem('doapizza_user_name');
        if (savedName) {
          userData.name = savedName;
        }
      }
      return userData;
    }
    return null;
  });
  const [loading, setLoading] = useState(false);

  const login = useCallback(async ({ phone, code }) => {
    setLoading(true);
    try {
      const cleanPhone = String(phone).replace(/\D/g, '').slice(-10);
      
      // Проверяем только код - если код 1234, авторизуем как клиента
      if (code === '1234' && cleanPhone.length === 10) {
        // Восстанавливаем сохраненное имя, если есть
        const savedName = localStorage.getItem('doapizza_user_name') || '';
        const userData = { 
          id: Date.now(), // Временный ID
          phone: cleanPhone, 
          role: 'CLIENT',
          name: savedName
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

  const updateUserName = useCallback((name) => {
    setUser((prevUser) => {
      if (!prevUser) return prevUser;
      const updatedUser = { ...prevUser, name };
      localStorage.setItem('doapizza_user', JSON.stringify(updatedUser));
      localStorage.setItem('doapizza_user_name', name);
      return updatedUser;
    });
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('doapizza_user');
    // Имя не удаляем при выходе, чтобы сохранить для следующего входа
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
