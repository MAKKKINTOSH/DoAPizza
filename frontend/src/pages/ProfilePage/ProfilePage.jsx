import styles from './ProfilePage.module.css';

export function ProfilePage() {
  return (
    <div className={styles.wrapper}>
      <h1 className={styles.title}>Профиль</h1>
      <p className={styles.lead}>
        Здесь собраны ваши сохранённые адреса, история заказов и бонусная программа.
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Мои адреса</h2>
        <p className={styles.text}>
          Здесь вы сможете сохранять любимые адреса доставки, чтобы заказывать ещё быстрее.
        </p>
        <div className={styles.placeholder}>
          <p>Список адресов пока пуст.</p>
          <p>Добавьте первый адрес при оформлении заказа.</p>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>История заказов</h2>
        <p className={styles.text}>
          Здесь появится список ваших прошлых заказов с деталями, адресами и статусами.
        </p>
        <div className={styles.placeholder}>
          <p>История заказов пока пуста.</p>
          <p>Сделайте первый заказ, и он появится здесь.</p>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Бонусы</h2>
        <p className={styles.text}>
          Здесь будет отображаться ваш бонусный баланс, история начислений и правила программы лояльности.
        </p>
        <div className={styles.placeholder}>
          <p>Пока бонусов нет.</p>
          <p>Оформляйте заказы, и бонусы начнут накапливаться.</p>
        </div>
      </section>
    </div>
  );
}

