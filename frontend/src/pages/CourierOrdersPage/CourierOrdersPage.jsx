import styles from './CourierOrdersPage.module.css';

export function CourierOrdersPage() {
  return (
    <div className={styles.wrapper}>
      <h1 className={styles.title}>Мои заказы (курьер)</h1>
      <p className={styles.lead}>
        Здесь курьер увидит список активных и выполненных доставок, адреса и время доставки.
      </p>
      <div className={styles.placeholder}>
        <p>Список заказов курьера пока пуст.</p>
        <p>Когда появятся заказы на доставку, они отобразятся здесь.</p>
      </div>
    </div>
  );
}

