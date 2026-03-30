import { useState, useEffect } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../features/auth';
import { useCart } from '../../entities/cart';
import { APP_NAME } from '../../shared/config';
import styles from './Header.module.css';

export function Header() {
  const { isAuthenticated, role, logout } = useAuth();
  const { items } = useCart();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const hasItems = items.length > 0;

  const navBtnClassName = ({ isActive }) =>
    `${styles.navBtn} ${isActive ? styles.active : ''}`;

  const navLinks = (
    <>
      <NavLink to="/" className={navBtnClassName} onClick={() => setMobileOpen(false)}>
        Меню
      </NavLink>
      <NavLink to="/about" className={navBtnClassName} onClick={() => setMobileOpen(false)}>
        О нас
      </NavLink>
      {hasItems && (
        <NavLink to="/checkout" className={navBtnClassName} onClick={() => setMobileOpen(false)}>
          Оформление
        </NavLink>
      )}
      {isAuthenticated && (
        <NavLink to="/profile" className={navBtnClassName} onClick={() => setMobileOpen(false)}>
          Профиль
        </NavLink>
      )}
      {isAuthenticated && role === 'COURIER' && (
        <NavLink to="/courier-orders" className={navBtnClassName} onClick={() => setMobileOpen(false)}>
          Мои заказы
        </NavLink>
      )}
      {role === 'ADMIN' && (
        <NavLink to="/admin" className={navBtnClassName} onClick={() => setMobileOpen(false)}>
          Админка
        </NavLink>
      )}
    </>
  );

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <NavLink to="/" className={styles.logo}>
          {APP_NAME}
        </NavLink>

        <nav className={styles.nav}>
          {navLinks}
        </nav>

        <div className={styles.right}>
          {isAuthenticated ? (
            <button
              type="button"
              onClick={handleLogout}
              className={`${styles.navBtn} ${styles.logoutBtn}`}
            >
              Выход
            </button>
          ) : (
            <button
              type="button"
              onClick={() => navigate('/login')}
              className={`${styles.navBtn} ${styles.loginBtn}`}
            >
              Вход
            </button>
          )}
        </div>

        <button
          type="button"
          className={`${styles.hamburger} ${mobileOpen ? styles.hamburgerOpen : ''}`}
          onClick={() => setMobileOpen((v) => !v)}
          aria-label="Меню"
        >
          <span />
          <span />
          <span />
        </button>
      </div>

      {mobileOpen && (
        <div className={styles.mobileMenu}>
          <nav className={styles.mobileNav}>
            {navLinks}
          </nav>
          <div className={styles.mobileAuthRow}>
            {isAuthenticated ? (
              <button
                type="button"
                onClick={() => { handleLogout(); setMobileOpen(false); }}
                className={styles.mobileAuthBtn}
              >
                Выход
              </button>
            ) : (
              <button
                type="button"
                onClick={() => { navigate('/login'); setMobileOpen(false); }}
                className={styles.mobileAuthBtn}
              >
                Войти
              </button>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
