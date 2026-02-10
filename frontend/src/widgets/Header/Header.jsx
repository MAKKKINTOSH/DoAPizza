import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../features/auth';
import { useCart } from '../../entities/cart';
import { APP_NAME } from '../../shared/config';
import styles from './Header.module.css';

export function Header() {
  const { isAuthenticated, role, logout } = useAuth();
  const { items } = useCart();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const hasItems = items.length > 0;

  const navBtnClassName = ({ isActive }) =>
    `${styles.navBtn} ${isActive ? styles.active : ''}`;

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <NavLink to="/" className={styles.logo}>
          {APP_NAME}
        </NavLink>

        <nav className={styles.nav}>
          <NavLink to="/" className={navBtnClassName}>
            Меню
          </NavLink>

          <NavLink to="/about" className={navBtnClassName}>
            О нас
          </NavLink>

          {hasItems && (
            <NavLink to="/checkout" className={navBtnClassName}>
              Оформление заказа
            </NavLink>
          )}

          {isAuthenticated && (
            <NavLink to="/profile" className={navBtnClassName}>
              Профиль
            </NavLink>
          )}

          {isAuthenticated && role === 'COURIER' && (
            <NavLink to="/courier-orders" className={navBtnClassName}>
              Мои заказы
            </NavLink>
          )}

          {role === 'ADMIN' && (
            <NavLink to="/admin" className={navBtnClassName}>
              Админка
            </NavLink>
          )}
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
      </div>
    </header>
  );
}
