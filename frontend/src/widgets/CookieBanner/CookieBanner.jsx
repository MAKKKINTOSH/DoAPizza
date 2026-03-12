import { useState, useEffect } from 'react';
import { Button } from '../../shared/ui/Button';
import styles from './CookieBanner.module.css';

const STORAGE_KEY = 'doapizza_cookies_accepted';

export function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      const accepted = localStorage.getItem(STORAGE_KEY);
      setVisible(!accepted);
    } catch {
      setVisible(true);
    }
  }, []);

  const handleAccept = () => {
    try {
      localStorage.setItem(STORAGE_KEY, 'true');
      setVisible(false);
    } catch {}
  };

  if (!visible) return null;

  return (
    <div className={styles.banner} role="dialog" aria-label="Уведомление о cookies">
      <div className={styles.content}>
        <p className={styles.text}>
          Мы используем файлы cookie для улучшения работы сайта, персонализации контента и анализа трафика.
          Продолжая пользоваться сайтом, вы соглашаетесь с нашей политикой в отношении cookies.
        </p>
        <Button variant="primary" size="md" onClick={handleAccept}>
          Понятно
        </Button>
      </div>
    </div>
  );
}
