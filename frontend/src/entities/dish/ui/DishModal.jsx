import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../../cart';
import { formatPrice } from '../../../shared/lib/formatPrice';
import { Button } from '../../../shared/ui/Button';
import { useToast } from '../../../shared/ui/Toast';
import styles from './DishModal.module.css';

export function DishModal({ dish, onClose }) {
  const variants = dish.variants || [];
  const [selectedVariant, setSelectedVariant] = useState(variants[0] || null);
  const [quantity, setQuantity] = useState(1);
  const { addItem } = useCart();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const hasSizes = variants.length > 1;
  const currentVariant = selectedVariant || variants[0];
  const weight = currentVariant?.weight ? parseFloat(currentVariant.weight) : null;
  const calories = currentVariant?.calories ? parseFloat(currentVariant.calories) : null;
  const totalPrice = parseFloat(currentVariant?.price || 0) * quantity;

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, []);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const buildItem = () => ({
    ...currentVariant,
    dish_name: dish.dish_name,
    dish_image: dish.dish_image,
  });

  const handleAddToCart = () => {
    if (!currentVariant) return;
    addItem(buildItem(), quantity);
    showToast(`${dish.dish_name} теперь в корзине`);
    onClose();
  };

  const handleBuyNow = () => {
    if (!currentVariant) return;
    addItem(buildItem(), quantity);
    onClose();
    navigate('/checkout');
  };

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.close} onClick={onClose} aria-label="Закрыть">
          ×
        </button>

        {dish.dish_image && (
          <div className={styles.imageWrap}>
            <img src={dish.dish_image} alt={dish.dish_name} className={styles.image} />
          </div>
        )}

        <div className={styles.body}>
          <h2 className={styles.title}>{dish.dish_name}</h2>

          {dish.dish_description && (
            <p className={styles.description}>{dish.dish_description}</p>
          )}

          {(weight > 0 || calories > 0) && (
            <div className={styles.meta}>
              {weight > 0 && <span>{weight} г</span>}
              {calories > 0 && <span>{calories} ккал</span>}
            </div>
          )}

          {hasSizes && (
            <>
              <p className={styles.sizeLabel}>Размер</p>
              <div className={styles.sizes}>
                {variants.map((v) => (
                  <button
                    key={v.id}
                    type="button"
                    className={`${styles.sizeBtn} ${selectedVariant?.id === v.id ? styles.active : ''}`}
                    onClick={() => setSelectedVariant(v)}
                  >
                    <span className={styles.sizeName}>{v.size}</span>
                    <span className={styles.sizePrice}>{formatPrice(parseFloat(v.price || 0))}</span>
                  </button>
                ))}
              </div>
            </>
          )}

          <div className={styles.orderRow}>
            <div className={styles.quantityControls}>
              <button
                type="button"
                className={styles.qBtn}
                onClick={() => setQuantity((q) => Math.max(1, q - 1))}
              >
                −
              </button>
              <span className={styles.quantity}>{quantity}</span>
              <button
                type="button"
                className={styles.qBtn}
                onClick={() => setQuantity((q) => q + 1)}
              >
                +
              </button>
            </div>
            <span className={styles.totalPrice}>{formatPrice(totalPrice)}</span>
          </div>

          <div className={styles.actions}>
            <Button variant="primary" fullWidth onClick={handleAddToCart}>
              В корзину
            </Button>
            <Button variant="secondary" fullWidth onClick={handleBuyNow}>
              Купить сейчас
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
