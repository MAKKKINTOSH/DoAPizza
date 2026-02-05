import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../features/auth';
import { MOCK_DISHES } from '../../entities/dish';
import styles from './AdminPage.module.css';

export function AdminPage() {
  const { isAuthenticated, role, loading } = useAuth();
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

  return (
    <>
      <h1 className={styles.title}>Админ-панель</h1>
      <p className={styles.subtitle}>Управление меню и заказами (мок-режим)</p>

      <section className={styles.section}>
        <h2>Блюда в меню ({MOCK_DISHES.length})</h2>
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
              {MOCK_DISHES.map((d) => (
                <tr key={d.id}>
                  <td>{d.name}</td>
                  <td>{d.category}</td>
                  <td>{d.basePrice} ₽</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
