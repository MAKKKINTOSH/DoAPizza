import { useState } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../features/auth';
import { useCart } from '../../entities/cart';
import { CartModal } from '../CartModal';
import { APP_NAME } from '../../shared/config';
import { formatPrice } from '../../shared/lib/formatPrice';
import styles from './MenuSidebar.module.css';

function scrollToSection(id) {
  const el = document.getElementById(id);
  el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

const PAGES = [
  { id: 'menu', label: 'Меню', path: '/' },
  { id: 'about', label: 'О нас', path: '/about' },
];

export function MenuSidebar({ menuSections = [] }) {
  const { pathname } = useLocation();
  const activePage =
    pathname === '/' ? 'menu' : pathname === '/about' ? 'about' : pathname === '/checkout' ? 'checkout' : null;
  const [cartOpen, setCartOpen] = useState(false);
  const { isAuthenticated, role, logout } = useAuth();
  const { items, totalPrice } = useCart();
  const navigate = useNavigate();

  const itemCount = items.reduce((sum, i) => sum + i.quantity, 0);

  const handlePageClick = (path) => {
    navigate(path);
    if (path === '/') {
      setTimeout(() => {
        const el = document.getElementById('menu');
        el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 0);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <>
      <aside className={styles.sidebar}>
        <NavLink to="/" className={styles.logo}>
          {APP_NAME}
        </NavLink>

        <nav className={styles.nav}>
          {activePage === 'menu' && menuSections.length > 0 && (
            <>
              <span className={styles.navLabel}>Разделы меню</span>
              {menuSections.map(({ id, label }) => (
                <button
                  key={id}
                  type="button"
                  className={styles.subLink}
                  onClick={() => scrollToSection(id)}
                >
                  {label}
                </button>
              ))}
            </>
          )}

          <span className={styles.navLabel}>Страницы</span>
          {PAGES.map(({ id, label, path }) => (
            <button
              key={id}
              type="button"
              className={`${styles.pageLink} ${activePage === id ? styles.pageLinkActive : ''}`}
              onClick={() => handlePageClick(path)}
            >
              {label}
            </button>
          ))}
          {items.length > 0 && (
            <button
              type="button"
              className={`${styles.pageLink} ${activePage === 'checkout' ? styles.pageLinkActive : ''}`}
              onClick={() => navigate('/checkout')}
            >
              Оформление заказа
            </button>
          )}
        </nav>

        <div className={styles.auth}>
          {isAuthenticated ? (
            <>
              {role === 'ADMIN' && (
                <NavLink to="/admin" className={styles.authLink}>
                  Админка
                </NavLink>
              )}
              <button type="button" onClick={handleLogout} className={styles.authLink}>
                Выход
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => navigate('/login')}
              className={styles.authLink}
            >
              Вход
            </button>
          )}
        </div>

        <div className={styles.footer}>
          <p className={styles.copyright}>© 2025 Доставка пиццы</p>
        </div>
      </aside>

      <button
        type="button"
        className={`${styles.cartFloating} ${cartOpen ? styles.cartFloatingActive : ''}`}
        onClick={() => setCartOpen(true)}
      >
        <span className={styles.cartFloatingRow}>
          <span className={styles.cartFloatingLabel}>Корзина</span>
          {itemCount > 0 && <span className={styles.cartFloatingBadge}>{itemCount}</span>}
        </span>
        {totalPrice > 0 && (
          <span className={styles.cartFloatingSum}>{formatPrice(totalPrice)}</span>
        )}
      </button>

      <CartModal isOpen={cartOpen} onClose={() => setCartOpen(false)} />
    </>
  );
}
