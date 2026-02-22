import { useNavigate } from 'react-router-dom';
import { useCart } from '../../entities/cart';
import { PIZZA_SIZES } from '../../entities/dish';
import { Button } from '../../shared/ui/Button';
import { formatPrice } from '../../shared/lib/formatPrice';
import styles from './CartModal.module.css';

export function CartModal({ isOpen, onClose }) {
  const { items, totalPrice, updateQuantity, removeItem, getItemPrice } = useCart();
  const navigate = useNavigate();

  if (!isOpen) return null;

  const handleCheckout = () => {
    onClose();
    navigate('/checkout');
  };

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>Корзина</h2>
          <button type="button" className={styles.close} onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>

        <div className={styles.body}>
          {items.length === 0 ? (
            <div className={styles.empty}>
              <p>Корзина пуста</p>
              <p className={styles.emptyHint}>Добавьте пиццу из меню</p>
            </div>
          ) : (
            <>
              <ul className={styles.list}>
                {items.map((item, idx) => {
                  const price = getItemPrice(item);
                  const sizeName =
                    item.sizeId && item.dish.hasSizes
                      ? PIZZA_SIZES.find((s) => s.id === item.sizeId)?.name
                      : null;

                  return (
                    <li key={`${item.dish.id}-${item.sizeId || 'x'}-${idx}`} className={styles.item}>
                      {item.dish.image && (
                        <div className={styles.itemImageWrap}>
                          <img src={item.dish.image} alt={item.dish.name} className={styles.itemImage} />
                        </div>
                      )}
                      <div className={styles.itemContent}>
                        <div className={styles.itemInfo}>
                          <span className={styles.itemName}>
                            {item.dish.name}
                            {sizeName && <span className={styles.size}> • {sizeName}</span>}
                          </span>
                          <span className={styles.itemPrice}>{formatPrice(price)}</span>
                        </div>
                        <div className={styles.itemRow}>
                          <div className={styles.quantity}>
                            <button
                              type="button"
                              onClick={() =>
                                updateQuantity(item.dish.id, item.sizeId, item.quantity - 1)
                              }
                            >
                              −
                            </button>
                            <span>{item.quantity}</span>
                            <button
                              type="button"
                              onClick={() =>
                                updateQuantity(item.dish.id, item.sizeId, item.quantity + 1)
                              }
                            >
                              +
                            </button>
                          </div>
                          <span className={styles.itemTotal}>{formatPrice(price * item.quantity)}</span>
                          <button
                            type="button"
                            className={styles.remove}
                            onClick={() => removeItem(item.dish.id, item.sizeId)}
                          >
                            Удалить
                          </button>
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>

              <div className={styles.footer}>
                <div className={styles.total}>
                  Итого: <strong>{formatPrice(totalPrice)}</strong>
                </div>
                <Button variant="primary" size="lg" fullWidth onClick={handleCheckout}>
                  Оформить заказ
                </Button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
