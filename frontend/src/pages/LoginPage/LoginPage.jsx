import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../features/auth';
import { DJANGO_ADMIN_URL } from '../../shared/config';
import { Button } from '../../shared/ui/Button';
import { Input } from '../../shared/ui/Input';
import styles from './LoginPage.module.css';

function formatPhoneDisplay(digits) {
  let d = (digits || '').replace(/\D/g, '').replace(/^8/, '7').slice(0, 11);
  if (d && !d.startsWith('7')) d = '7' + d;
  const p1 = d.slice(1, 4);
  const p2 = d.slice(4, 7);
  const p3 = d.slice(7, 9);
  const p4 = d.slice(9, 11);
  if (!d || d === '7') return '+7 ';
  let out = `+7 (${p1}`;
  if (p2) out += `) ${p2}`;
  if (p3) out += ` - ${p3}`;
  if (p4) out += ` - ${p4}`;
  return out.replace(/\s*-\s*$/g, '').trim();
}

function maskPhoneForDisplay(phoneDigits) {
  const d = (phoneDigits || '').replace(/\D/g, '').replace(/^8/, '7').slice(1, 11);
  const p1 = d.slice(0, 3);
  const p2 = d.length > 3 ? '***' : '___';
  const p3 = d.length > 6 ? '**' : '__';
  const p4 = d.length > 8 ? d.slice(8, 10) : '__';
  return `+7 (${p1 || '___'}) ${p2} - ${p3} - ${p4}`;
}

const CODE_LENGTH = 4;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [phoneDigits, setPhoneDigits] = useState('');
  const [code, setCode] = useState(['', '', '', '']);
  const [stage, setStage] = useState('phone');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const codeRefs = useRef([null, null, null, null]);

  const formattedPhone = formatPhoneDisplay(phoneDigits);
  const maskedPhone = maskPhoneForDisplay(phoneDigits);
  const cleanPhone = phoneDigits.replace(/\D/g, '').replace(/^8/, '7').slice(-10);

  const handlePhoneChange = (value) => {
    let digits = value.replace(/\D/g, '').replace(/^8/, '7').slice(0, 11);
    if (digits && !digits.startsWith('7')) digits = '7' + digits;
    setPhoneDigits(digits);
  };

  const handleRequestCode = (e) => {
    e.preventDefault();
    setError('');
    if (cleanPhone.length !== 10) {
      setError('Введите корректный номер телефона');
      return;
    }
    setSending(true);
    // В реальном проекте — запрос на отправку кода (Telegram / SMS)
    setTimeout(() => {
      setStage('code');
      setCode(['', '', '', '']);
      setSending(false);
    }, 300);
  };

  const setCodeDigit = (index, digit) => {
    const onlyDigit = digit.replace(/\D/g, '').slice(-1);
    const next = [...code];
    next[index] = onlyDigit;
    setCode(next);
    if (onlyDigit && index < CODE_LENGTH - 1) codeRefs.current[index + 1]?.focus();
  };

  const handleCodeKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      codeRefs.current[index - 1]?.focus();
    }
  };

  const handleCodePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, CODE_LENGTH);
    const next = [...code];
    pasted.split('').forEach((d, i) => { next[i] = d; });
    setCode(next);
    const focusIndex = Math.min(pasted.length, CODE_LENGTH - 1);
    codeRefs.current[focusIndex]?.focus();
  };

  const codeString = code.join('');
  useEffect(() => {
    if (stage !== 'code' || codeString.length !== CODE_LENGTH) return;
    const submit = async () => {
      setError('');
      const result = await login({ phone: cleanPhone, code: codeString });
      if (result.success) navigate('/');
      else setError(result.message || 'Неверный код. Проверьте и попробуйте снова.');
    };
    submit();
  }, [stage, codeString, cleanPhone, login, navigate]);

  const handleResendCode = (e) => {
    e.preventDefault();
    setError('');
    setCode(['', '', '', '']);
    // Повторная отправка кода на бэкенд
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.card}>
        <button
          type="button"
          className={styles.close}
          onClick={() => navigate('/')}
          aria-label="Закрыть"
        >
          ×
        </button>

        {stage === 'phone' && (
          <>
            <h1 className={styles.title}>Укажите номер телефона</h1>
            <p className={styles.subtitle}>Чтобы получить код для входа</p>
            <form onSubmit={handleRequestCode} className={styles.form}>
              {error && <p className={styles.error}>{error}</p>}
              <Input
                type="tel"
                value={formattedPhone}
                onChange={handlePhoneChange}
                placeholder="+7 (___) ___ - __ - __"
                autoComplete="tel"
                className={styles.phoneInput}
              />
              <Button type="submit" variant="primary" size="lg" fullWidth disabled={sending}>
                Получить код
              </Button>
            </form>
          </>
        )}

        {stage === 'code' && (
          <>
            <h1 className={styles.title}>Введите код из Telegram</h1>
            <p className={styles.subtitle}>Отправили на номер {maskedPhone}</p>
            {error && <p className={styles.error}>{error}</p>}
            <div className={styles.codeRow} onPaste={handleCodePaste}>
              {code.map((digit, i) => (
                <input
                  key={i}
                  ref={(el) => { codeRefs.current[i] = el; }}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => setCodeDigit(i, e.target.value)}
                  onKeyDown={(e) => handleCodeKeyDown(i, e)}
                  className={styles.codeInput}
                  placeholder="-"
                  aria-label={`Цифра ${i + 1}`}
                />
              ))}
            </div>
            <button type="button" className={styles.resend} onClick={handleResendCode}>
              Отправить код повторно
            </button>
          </>
        )}
      </div>

      <a href={DJANGO_ADMIN_URL} className={styles.adminLink}>
        Войти как администратор
      </a>
    </div>
  );
}
