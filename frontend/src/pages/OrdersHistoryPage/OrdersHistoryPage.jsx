import styles from './OrdersHistoryPage.module.css';

export function OrdersHistoryPage() {
  return (
    <div className={styles.wrapper}>
      <h1 className={styles.title}>История заказов</h1>
      <p className={styles.lead}>
        Здесь появится список ваших прошлых заказов с деталями, адресами и статусами.
      </p>
      <div className={styles.placeholder}>
        <p>История заказов пока пуста.</p>
        <p>Сделайте первый заказ, и он появится здесь.</p>
      </div>
    </div>
  );
}

