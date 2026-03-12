import { useMenu } from '../../features/menu';
import { DishCard, PROMO_BANNERS } from '../../entities/dish';
import styles from './MenuPage.module.css';

export function MenuPage() {
  const { dishes, categories, loading, error } = useMenu();

  const categoryNames = Object.fromEntries((categories || []).map((c) => [c.id, c.name]));
  const popularDishes = dishes.slice(0, 4);
  const grouped = (dishes || []).reduce((acc, dish) => {
    const catId = dish.category?.id;
    const catName = dish.category?.name || categoryNames[catId] || 'Другое';
    if (!acc[catName]) acc[catName] = [];
    acc[catName].push(dish);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className={styles.hero}>
        <p>Загрузка меню...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.hero}>
        <p className={styles.errorText}>{error}</p>
        <p className={styles.errorHint}>Проверьте, что backend запущен на http://localhost:8000</p>
      </div>
    );
  }

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

      {Object.entries(grouped).map(([category, list]) => {
        const sectionId = list[0]?.category?.id
          ? `cat-${list[0].category.id}`
          : category.toLowerCase().replace(/\s+/g, '-');
        return (
          <section key={category} id={sectionId} className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>{category}</h2>
              <p className={styles.sectionDesc}>{list.length} позиций</p>
            </div>
            <div className={styles.grid}>
              {list.map((dish) => (
                <DishCard key={dish.id} dish={dish} />
              ))}
            </div>
          </section>
        );
      })}
    </>
  );
}
