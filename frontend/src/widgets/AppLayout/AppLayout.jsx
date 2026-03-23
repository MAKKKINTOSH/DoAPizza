import { useMemo, useState, useEffect } from 'react';
import { Outlet, useLocation, NavLink } from 'react-router-dom';
import { Header } from '../Header';
import { useCart } from '../../entities/cart';
import { useMenu } from '../../features/menu';
import { CartModal } from '../CartModal';
import { CookieBanner } from '../CookieBanner';
import { formatPrice } from '../../shared/lib/formatPrice';
import { WORKING_HOURS } from '../../pages/AboutPage/AboutPage';
import styles from './AppLayout.module.css';

export function AppLayout() {
  const location = useLocation();
  const [activeSectionId, setActiveSectionId] = useState(null);
  const [cartOpen, setCartOpen] = useState(false);
  const { items, totalPrice } = useCart();
  const { dishes, categories } = useMenu();

  const menuSections = useMemo(() => {
    const catMap = Object.fromEntries((categories || []).map((c) => [c.id, c.name]));
    const grouped = (dishes || []).reduce((acc, dish) => {
      const catName = dish.category?.name || catMap[dish.category?.id] || 'Другое';
      if (!acc[catName]) acc[catName] = [];
      acc[catName].push(dish);
      return acc;
    }, {});
    const list = [];
    if (dishes?.length > 0) list.push({ id: 'popular', label: 'Популярное' });
    Object.keys(grouped).forEach((label) => {
      const listDishes = grouped[label];
      const id = listDishes[0]?.category?.id ? `cat-${listDishes[0].category.id}` : label.toLowerCase().replace(/\s+/g, '-');
      list.push({ id, label });
    });
    return list;
  }, [dishes, categories]);

  const isMenuPage = location.pathname === '/';

  const itemCount = items.reduce((sum, i) => sum + i.quantity, 0);

  const handleCategoryClick = (id) => {
    setActiveSectionId(id);
    const el = document.getElementById(id);
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  useEffect(() => {
    if (!isMenuPage || menuSections.length === 0) return;

    const handleScroll = () => {
      const sections = menuSections
        .map(({ id }) => {
          const el = document.getElementById(id);
          if (!el) return null;
          const rect = el.getBoundingClientRect();
          return { id, top: rect.top };
        })
        .filter(Boolean);

      if (sections.length === 0) return;

      const headerOffset = 120;

      const above = sections
        .filter((s) => s.top <= headerOffset)
        .sort((a, b) => b.top - a.top)[0];

      const current =
        above ||
        sections.sort((a, b) => Math.abs(a.top - headerOffset) - Math.abs(b.top - headerOffset))[0];

      if (current && current.id !== activeSectionId) {
        setActiveSectionId(current.id);
      }
    };

    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [isMenuPage, menuSections, activeSectionId]);

  return (
    <div className={styles.layout}>
      <Header />

      {isMenuPage && menuSections.length > 0 && (
        <div className={styles.menuCategoriesBar}>
          <div className={styles.menuCategoriesInner}>
            {menuSections.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                className={`${styles.menuCategoryBtn} ${
                  activeSectionId === id ? styles.menuCategoryBtnActive : ''
                }`}
                onClick={() => handleCategoryClick(id)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      <main className={styles.main}>
        <div className={styles.content}>
          <Outlet />
        </div>
      </main>

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
          <>
            <span className={styles.cartFloatingDivider} />
            <span className={styles.cartFloatingSum}>{formatPrice(totalPrice)}</span>
          </>
        )}
      </button>

      <CartModal isOpen={cartOpen} onClose={() => setCartOpen(false)} />

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerTop}>
            <div className={styles.footerCol}>
              <span className={styles.footerLogo}>DoAPizza</span>
              <p className={styles.footerText}>
                Доставка пиццы и любимых блюд.<br />Готовим из свежих продуктов, доставляем горячим.
              </p>
            </div>

            <div className={styles.footerCol}>
              <span className={styles.footerColTitle}>Навигация</span>
              <nav className={styles.footerNav}>
                <NavLink to="/" className={styles.footerLink}>Меню</NavLink>
                <NavLink to="/about" className={styles.footerLink}>О нас</NavLink>
                <NavLink to="/privacy" className={styles.footerLink}>Политика конфиденциальности</NavLink>
              </nav>
            </div>

            <div className={styles.footerCol}>
              <span className={styles.footerColTitle}>Контакты</span>
              <p className={styles.footerText}>г. Иркутск, ул. Лермонтова, 83</p>
              <p className={styles.footerText}>+7 (914) 000-00-00</p>
              <p className={styles.footerText}>doapizza@example.com</p>
            </div>

            <div className={styles.footerCol}>
              <span className={styles.footerColTitle}>Часы работы</span>
              <p className={styles.footerText}>{WORKING_HOURS}</p>
            </div>
          </div>

          <div className={styles.footerBottom}>
            <p className={styles.footerCopy}>© 2025 DoAPizza. Все права защищены.</p>
          </div>
        </div>
      </footer>

      <CookieBanner />
    </div>
  );
}
