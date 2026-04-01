import { useState } from 'react';
import { AddToCartButton } from '../../../features/add-to-cart';
import { formatPrice } from '../../../shared/lib/formatPrice';
import { DishModal } from './DishModal';
import styles from './DishCard.module.css';

/**
 * dish — объект из API: { id, dish_name, dish_image, dish_description, category, variants: [...] }
 */
export function DishCard({ dish, variant }) {
  const [modalOpen, setModalOpen] = useState(false);

  const variants = dish.variants || [];
  const hasSizes = variants.length > 1;
  const minPrice = variants.length
    ? Math.min(...variants.map((v) => parseFloat(v.price || 0)))
    : 0;
  const priceText = hasSizes ? `от ${formatPrice(minPrice)}` : formatPrice(minPrice);
  const firstV = variants[0];
  const weight = firstV?.weight ? parseFloat(firstV.weight) : null;
  const calories = firstV?.calories ? parseFloat(firstV.calories) : null;

  return (
    <>
      <article
        className={`${styles.card} ${variant === 'compact' ? styles.compact : ''}`}
        onClick={() => setModalOpen(true)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setModalOpen(true); }}
      >
        <div className={styles.imageWrap}>
          {dish.dish_image ? (
            <img src={dish.dish_image} alt={dish.dish_name} className={styles.image} />
          ) : (
            <div className={styles.placeholder}>Пицца</div>
          )}
        </div>
        <div className={styles.body}>
          <h3 className={styles.title}>{dish.dish_name}</h3>
          {dish.dish_description && (
            <p className={styles.description}>{dish.dish_description}</p>
          )}
          <div className={styles.meta}>
            {weight > 0 && <span>{weight} г</span>}
            {calories > 0 && <span>{calories} ккал</span>}
          </div>
          <div className={styles.footer}>
            <span className={styles.price}>{priceText}</span>
            {/* stopPropagation чтобы кнопка не открывала модалку карточки */}
            <div onClick={(e) => e.stopPropagation()}>
              <AddToCartButton dish={dish} />
            </div>
          </div>
        </div>
      </article>

      {modalOpen && (
        <DishModal dish={dish} onClose={() => setModalOpen(false)} />
      )}
    </>
  );
}
