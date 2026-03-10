import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../features/auth';
import { useMenu } from '../../features/menu';
import styles from './AdminPage.module.css';

export function AdminPage() {
  const { isAuthenticated, role, loading } = useAuth();
  const { dishes, loading: menuLoading } = useMenu();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      navigate('/login');
    } else if (!loading && role !== 'ADMIN') {
      navigate('/');
    }
  }, [isAuthenticated, role, loading, navigate]);

  if (loading) {
    return <div className={styles.loading}>Загрузка...</div>;
  }

  if (!isAuthenticated || role !== 'ADMIN') {
    return null;
  }

  const flatDishes = (dishes || []).flatMap((d) =>
    (d.variants || []).map((v) => ({
      name: d.dish_name,
      category: d.category?.name || d.category,
      price: parseFloat(v.price || 0),
    }))
  );
  const uniqueDishes = flatDishes.filter(
    (d, i, arr) => arr.findIndex((x) => x.name === d.name && x.price === d.price) === i
  );

  return (
    <>
      <h1 className={styles.title}>Админ-панель</h1>
      <p className={styles.subtitle}>Управление меню и заказами</p>

      <section className={styles.section}>
        <h2>Блюда в меню ({uniqueDishes.length})</h2>
        {menuLoading ? (
          <p>Загрузка...</p>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Название</th>
                  <th>Категория</th>
                  <th>Цена</th>
                </tr>
              </thead>
              <tbody>
                {uniqueDishes.map((d, idx) => (
                  <tr key={`${d.name}-${d.price}-${idx}`}>
                    <td>{d.name}</td>
                    <td>{d.category}</td>
                    <td>{d.price} ₽</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
