import { useMemo } from 'react';
import { Outlet } from 'react-router-dom';
import { MenuSidebar } from '../MenuSidebar';
import { MOCK_DISHES, CATEGORY_NAMES } from '../../entities/dish';
import styles from './AppLayout.module.css';

export function AppLayout() {
  const menuSections = useMemo(() => {
    const popularDishes = MOCK_DISHES.filter((d) => d.isPopular);
    const grouped = MOCK_DISHES.reduce((acc, dish) => {
      const cat = CATEGORY_NAMES[dish.category] || dish.category;
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(dish);
      return acc;
    }, {});
    const list = [];
    if (popularDishes.length > 0) list.push({ id: 'popular', label: 'Популярное' });
    Object.keys(grouped).forEach((label) => {
      const dishes = grouped[label];
      const id = dishes[0]?.category || label.toLowerCase().replace(/\s+/g, '-');
      list.push({ id, label });
    });
    return list;
  }, []);

  return (
    <div className={styles.layout}>
      <MenuSidebar menuSections={menuSections} />
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
