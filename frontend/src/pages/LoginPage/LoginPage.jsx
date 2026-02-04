import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../features/auth';
import { Button } from '../../shared/ui/Button';
import { Input } from '../../shared/ui/Input';
import styles from './LoginPage.module.css';

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const cleanPhone = String(phone).replace(/\D/g, '').slice(-10);
    if (cleanPhone.length !== 10) {
      setError('Введите корректный номер телефона');
      return;
    }

    const result = await login({ phone: cleanPhone, password });

    if (result.success) {
      if (result.role === 'ADMIN') {
        navigate('/admin');
      } else {
        navigate('/');
      }
    } else {
      setError(result.message || 'Ошибка входа');
    }
  };

  return (
    <div className={styles.wrapper}>
        <h1 className={styles.title}>Вход</h1>
        <p className={styles.hint}>
          Введите телефон и пароль. Администраторы перенаправляются в админ-панель.
        </p>

        <form onSubmit={handleSubmit} className={styles.form}>
          {error && <p className={styles.error}>{error}</p>}
          <Input
            label="Телефон"
            type="tel"
            value={phone}
            onChange={setPhone}
            placeholder="999 123 45 67"
            required
            autoComplete="tel"
          />
          <Input
            label="Пароль"
            type="password"
            value={password}
            onChange={setPassword}
            placeholder="••••••"
            required
          />
          <Button type="submit" variant="primary" size="lg" fullWidth>
            Войти
          </Button>
        </form>

        <Link to="/" className={styles.back}>
          ← Назад в меню
        </Link>
      </div>
  );
}
