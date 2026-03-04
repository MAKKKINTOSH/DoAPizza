import styles from './AboutPage.module.css';

export function AboutPage() {
  return (
    <>
      <div className={styles.hero}>
        <h1 className={styles.title}>О нас</h1>
        <p className={styles.lead}>
          DoAPizza — доставка пиццы и любимых блюд. Готовим из свежих продуктов,
          доставляем горячим.
        </p>
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Кто мы</h2>
        <p className={styles.text}>
          Мы любим пиццу и верим, что хорошая доставка — это быстрый заказ,
          свежие ингредиенты и внимание к каждому клиенту. Наша команда готовит
          пиццу по проверенным рецептам и привозит её к вам.
        </p>
        <p className={styles.text}>
          В меню — классические и авторские пиццы, напитки и десерты. Выбирайте
          на сайте, оформляйте заказ — мы позаботимся об остальном.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Контакты и адрес</h2>
        <p className={styles.text}>
          Работаем каждый день. Заказы принимаем на сайте и по телефону.
        </p>
        <div className={styles.mapBlock}>
          <div className={styles.mapPlaceholder}>
            <span>Карта</span>
            <p>Здесь будет карта (Яндекс.Карты / Google Maps)</p>
          </div>
        </div>
        <p className={styles.address}>
          Адрес: г. Москва, ул. Примерная, д. 1
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Фотографии</h2>
        <div className={styles.gallery}>
          <div className={styles.galleryItem} />
          <div className={styles.galleryItem} />
          <div className={styles.galleryItem} />
        </div>
      </section>
    </>
  );
}
