import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../features/auth';
import { DJANGO_ADMIN_URL } from '../../shared/config';
import { Button } from '../../shared/ui/Button';
import { Input } from '../../shared/ui/Input';
import styles from './LoginPage.module.css';

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [stage, setStage] = useState('phone'); // 'phone' | 'code'
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');

  const handlePhoneChange = (value) => {
    const digits = String(value).replace(/\D/g, '');
    // Оставляем максимум 11 цифр, добавляя ведущую 7, если её нет
    let withCountry = digits;
    if (!withCountry.startsWith('7')) {
      withCountry = `7${withCountry}`;
    }
    withCountry = withCountry.slice(0, 11);

    // Формат: 7900 000 00 01
    const p1 = withCountry.slice(0, 1); // 7
    const p2 = withCountry.slice(1, 4); // 900
    const p3 = withCountry.slice(4, 7); // 000
    const p4 = withCountry.slice(7, 9); // 00
    const p5 = withCountry.slice(9, 11); // 01

    let formatted = p1;
    if (p2) formatted += ` ${p2}`;
    if (p3) formatted += ` ${p3}`;
    if (p4) formatted += ` ${p4}`;
    if (p5) formatted += ` ${p5}`;

    setPhone(formatted.trim());
  };

  const handleRequestCode = (e) => {
    e.preventDefault();
    setError('');
    setInfo('');
    const cleanPhone = String(phone).replace(/\D/g, '').slice(-10);
    if (cleanPhone.length !== 10) {
      setError('Введите корректный номер телефона');
      return;
    }

    // В реальном проекте здесь будет запрос на отправку кода (SMS / Telegram-бот).
    // В демо код фиксированный: 12345.
    setStage('code');
    setInfo('Мы отправили код в SMS или Telegram. В демо-версии используйте код 12345.');
  };

  const handleSubmitCode = async (e) => {
    e.preventDefault();
    setError('');
    setInfo('');
    const cleanPhone = String(phone).replace(/\D/g, '').slice(-10);
    if (cleanPhone.length !== 10) {
      setError('Введите корректный номер телефона');
      return;
    }

    if (!code) {
      setError('Введите код из SMS или Telegram');
      return;
    }

    const result = await login({ phone: cleanPhone, code });

    if (result.success) {
      navigate('/');
    } else {
      setError(result.message || 'Ошибка входа. Проверьте код и номер телефона.');
    }
  };

  return (
    <div className={styles.wrapper}>
        <h1 className={styles.title}>Вход</h1>
        <p className={styles.hint}>
          Введите номер телефона. Мы отправим код для входа через SMS или Telegram-бота.
          В демо-версии используйте номера:
          клиент — 7900 000 00 01, курьер — 7900 000 00 02, код — 12345.
        </p>

        <form
          onSubmit={stage === 'phone' ? handleRequestCode : handleSubmitCode}
          className={styles.form}
        >
          {error && <p className={styles.error}>{error}</p>}
          {info && !error && <p className={styles.info}>{info}</p>}
          <Input
            label="Телефон"
            type="tel"
            value={phone}
            onChange={handlePhoneChange}
            placeholder="7900 000 00 01"
            required
            autoComplete="tel"
          />
          {stage === 'code' && (
            <Input
              label="Код из SMS / Telegram"
              type="text"
              value={code}
              onChange={setCode}
              placeholder="Например, 12345"
              required
            />
          )}
          <Button type="submit" variant="primary" size="lg" fullWidth>
            {stage === 'phone' ? 'Получить код' : 'Войти'}
          </Button>
        </form>

        <a
          href={DJANGO_ADMIN_URL}
          className={styles.adminLink}
        >
          Войти как администратор
        </a>

      </div>
  );
}
