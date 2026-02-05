import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../features/auth';
import { useCart } from '../../entities/cart';
import { CartModal } from '../CartModal';
import { APP_NAME } from '../../shared/config';
import { formatPrice } from '../../shared/lib/formatPrice';
import styles from './Header.module.css';

export function Header() {
  const [cartOpen, setCartOpen] = useState(false);
  const { isAuthenticated, role, logout } = useAuth();
  const { items, totalPrice } = useCart();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const itemCount = items.reduce((sum, i) => sum + i.quantity, 0);

  return (
    <>
      <header className={styles.header}>
        <div className={styles.inner}>
          <NavLink to="/" className={styles.logo}>
            {APP_NAME}
          </NavLink>

          <nav className={styles.nav}>
            <NavLink to="/" className={({ isActive }) => `${styles.navBtn} ${isActive ? styles.active : ''}`}>
              Меню
            </NavLink>
            <button
              type="button"
              className={`${styles.navBtn} ${cartOpen ? styles.active : ''}`}
              onClick={() => setCartOpen(true)}
            >
              Корзина
              {itemCount > 0 && <span className={styles.badge}>{itemCount}</span>}
              {totalPrice > 0 && <span className={styles.sum}>{formatPrice(totalPrice)}</span>}
            </button>
          </nav>

          <div className={styles.right}>
            {isAuthenticated ? (
              <>
                {role === 'ADMIN' && (
                  <NavLink to="/admin" className={styles.navBtn}>
                    Админка
                  </NavLink>
                )}
                <button type="button" onClick={handleLogout} className={styles.navBtn}>
                  Выход
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => navigate('/login')}
                className={styles.navBtn}
              >
                Вход
              </button>
            )}
          </div>
        </div>
      </header>

      <CartModal isOpen={cartOpen} onClose={() => setCartOpen(false)} />
    </>
  );
}
