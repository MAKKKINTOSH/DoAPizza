import styles from './AddressesPage.module.css';

export function AddressesPage() {
  return (
    <div className={styles.wrapper}>
      <h1 className={styles.title}>Мои адреса</h1>
      <p className={styles.lead}>
        Здесь вы сможете сохранять любимые адреса доставки, чтобы заказывать ещё быстрее.
      </p>
      <div className={styles.placeholder}>
        <p>Список адресов пока пуст.</p>
        <p>Добавьте первый адрес при оформлении заказа.</p>
      </div>
    </div>
  );
}

