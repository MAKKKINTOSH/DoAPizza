import styles from './PrivacyPage.module.css';

export function PrivacyPage() {
  return (
    <>
      <div className={styles.hero}>
        <h1 className={styles.title}>Политика конфиденциальности</h1>
        <p className={styles.lead}>
          DoAPizza уважает вашу конфиденциальность и защищает персональные данные пользователей.
        </p>
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>1. Какие данные мы собираем</h2>
        <p className={styles.text}>
          При оформлении заказа и авторизации мы обрабатываем: номер телефона, имя,
          электронную почту, адрес доставки. Эти данные необходимы для связи с вами
          и выполнения заказа.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>2. Как мы используем данные</h2>
        <p className={styles.text}>
          Персональные данные используются для: приёма и обработки заказов,
          отправки кода подтверждения для входа, связи по вопросам доставки,
          улучшения качества сервиса.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>3. Хранение и защита</h2>
        <p className={styles.text}>
          Данные хранятся в защищённой среде. Мы не передаём персональные данные
          третьим лицам, за исключением случаев, необходимых для исполнения заказа
          (например, передача адреса курьерской службе).
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>4. Ваши права</h2>
        <p className={styles.text}>
          Вы можете запросить доступ к своим данным, их изменение или удаление.
          Для этого свяжитесь с нами по контактам, указанным на сайте.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>5. Cookies</h2>
        <p className={styles.text}>
          Сайт использует файлы cookie для работы корзины, сохранения авторизации
          и улучшения удобства использования. Продолжая пользоваться сайтом,
          вы соглашаетесь с использованием cookies.
        </p>
      </section>
    </>
  );
}
