import styles from './BonusesPage.module.css';

export function BonusesPage() {
  return (
    <div className={styles.wrapper}>
      <h1 className={styles.title}>Бонусы</h1>
      <p className={styles.lead}>
        Здесь будет отображаться ваш бонусный баланс, история начислений и правил программы лояльности.
      </p>
      <div className={styles.placeholder}>
        <p>Пока бонусов нет.</p>
        <p>Оформляйте заказы, и бонусы начнут накапливаться.</p>
      </div>
    </div>
  );
}

