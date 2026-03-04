import { useState } from 'react';
import { useCart } from '../../../entities/cart';
import { PIZZA_SIZES } from '../../../entities/dish';
import { Button } from '../../../shared/ui/Button';
import { formatPrice } from '../../../shared/lib/formatPrice';
import styles from './AddToCartButton.module.css';

export function AddToCartButton({ dish, onAdded }) {
  const [open, setOpen] = useState(false);
  const [sizeId, setSizeId] = useState('medium');
  const [quantity, setQuantity] = useState(1);
  const { addItem } = useCart();

  const handleAdd = () => {
    if (dish.hasSizes) {
      addItem(dish, quantity, sizeId);
    } else {
      addItem(dish, quantity);
    }
    onAdded?.();
    setOpen(false);
  };

  const handleQuickAdd = () => {
    if (dish.hasSizes) {
      setOpen(true);
    } else {
      addItem(dish, 1);
      onAdded?.();
    }
  };

  if (!open) {
    return (
      <Button variant="primary" size="md" fullWidth onClick={handleQuickAdd}>
        В корзину
      </Button>
    );
  }

  return (
    <div className={styles.modal} onClick={() => setOpen(false)}>
      <div className={styles.content} onClick={(e) => e.stopPropagation()}>
        <h4 className={styles.title}>Выберите размер</h4>
        <div className={styles.sizes}>
          {PIZZA_SIZES.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`${styles.sizeBtn} ${sizeId === s.id ? styles.active : ''}`}
              onClick={() => setSizeId(s.id)}
            >
              <span className={styles.sizeName}>{s.name}</span>
              <span className={styles.sizePrice}>
                {formatPrice(Math.round(dish.basePrice * s.multiplier))}
              </span>
            </button>
          ))}
        </div>
        <div className={styles.quantityRow}>
          <label>Количество:</label>
          <div className={styles.quantityControls}>
            <button
              type="button"
              onClick={() => setQuantity((q) => Math.max(1, q - 1))}
            >
              −
            </button>
            <span>{quantity}</span>
            <button type="button" onClick={() => setQuantity((q) => q + 1)}>
              +
            </button>
          </div>
        </div>
        <Button variant="primary" fullWidth onClick={handleAdd}>
          Добавить в корзину
        </Button>
      </div>
    </div>
  );
}
