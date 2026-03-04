import { MOCK_DISHES, CATEGORY_NAMES, PROMO_BANNERS } from '../../entities/dish';
import { DishCard } from '../../entities/dish';
import styles from './MenuPage.module.css';

export function MenuPage() {
  const popularDishes = MOCK_DISHES.filter((d) => d.isPopular);
  const grouped = MOCK_DISHES.reduce((acc, dish) => {
    const cat = CATEGORY_NAMES[dish.category] || dish.category;
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(dish);
    return acc;
  }, {});

  return (
    <>
      <div id="menu" className={styles.hero}>
        <h1 className={styles.title}>Меню</h1>
        <p className={styles.subtitle}>Свежая пицца с доставкой</p>
      </div>

      <div className={styles.promoStrip}>
        {PROMO_BANNERS.map((b) => (
          <div key={b.id} className={styles.promoCard}>
            <span className={styles.promoAccent}>{b.accent}</span>
            <h3 className={styles.promoTitle}>{b.title}</h3>
            <p className={styles.promoSubtitle}>{b.subtitle}</p>
          </div>
        ))}
      </div>

      {popularDishes.length > 0 && (
        <section id="popular" className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>Популярное</h2>
            <p className={styles.sectionDesc}>Выбор наших гостей</p>
          </div>
          <div className={styles.popularGrid}>
            {popularDishes.map((dish) => (
              <DishCard key={dish.id} dish={dish} variant="compact" />
            ))}
          </div>
        </section>
      )}

      {Object.entries(grouped).map(([category, dishes]) => {
        const sectionId = dishes[0]?.category || category.toLowerCase().replace(/\s+/g, '-');
        return (
          <section key={category} id={sectionId} className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>{category}</h2>
              <p className={styles.sectionDesc}>{dishes.length} позиций</p>
            </div>
            <div className={styles.grid}>
              {dishes.map((dish) => (
                <DishCard key={dish.id} dish={dish} />
              ))}
            </div>
          </section>
        );
      })}
    </>
  );
}
