import { useState } from 'react';
import { useCart } from '../../../entities/cart';
import { Button } from '../../../shared/ui/Button';
import { formatPrice } from '../../../shared/lib/formatPrice';
import styles from './AddToCartButton.module.css';

/**
 * dish — объект из API: { id, dish_name, dish_image, variants: [{ id, size, size_value, price }] }
 */
export function AddToCartButton({ dish, onAdded }) {
  const [open, setOpen] = useState(false);
  const [selectedVariant, setSelectedVariant] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const { addItem } = useCart();

  const variants = dish.variants || [];
  const hasSizes = variants.length > 1;
  const currentVariant = selectedVariant || variants[0];

  const handleAdd = () => {
    if (!currentVariant) return;
    const v = {
      ...currentVariant,
      dish_name: dish.dish_name,
      dish_image: dish.dish_image,
    };
    addItem(v, quantity);
    onAdded?.();
    setOpen(false);
  };

  const handleQuickAdd = () => {
    if (hasSizes) {
      setSelectedVariant(variants[0]);
      setOpen(true);
    } else if (variants[0]) {
      const v = {
        ...variants[0],
        dish_name: dish.dish_name,
        dish_image: dish.dish_image,
      };
      addItem(v, 1);
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
          {variants.map((v) => (
            <button
              key={v.id}
              type="button"
              className={`${styles.sizeBtn} ${currentVariant?.id === v.id ? styles.active : ''}`}
              onClick={() => setSelectedVariant(v)}
            >
              <span className={styles.sizeName}>{v.size}</span>
              <span className={styles.sizePrice}>{formatPrice(parseFloat(v.price || 0))}</span>
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
