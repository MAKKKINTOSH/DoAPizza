import { AddToCartButton } from '../../../features/add-to-cart';
import { formatPrice } from '../../../shared/lib/formatPrice';
import styles from './DishCard.module.css';

export function DishCard({ dish, variant }) {
  const priceText = dish.hasSizes
    ? `от ${formatPrice(dish.basePrice)}`
    : formatPrice(dish.basePrice);

  return (
    <article className={`${styles.card} ${variant === 'compact' ? styles.compact : ''}`}>
      <div className={styles.imageWrap}>
        {dish.image ? (
          <img src={dish.image} alt={dish.name} className={styles.image} />
        ) : (
          <div className={styles.placeholder}>Пицца</div>
        )}
      </div>
      <div className={styles.body}>
        <h3 className={styles.title}>{dish.name}</h3>
        {dish.description && (
          <p className={styles.description}>{dish.description}</p>
        )}
        <div className={styles.meta}>
          {dish.weight && <span>{dish.weight} г</span>}
          {dish.calories && <span>{dish.calories} ккал</span>}
        </div>
        <div className={styles.footer}>
          <span className={styles.price}>{priceText}</span>
          <AddToCartButton dish={dish} />
        </div>
      </div>
    </article>
  );
}
