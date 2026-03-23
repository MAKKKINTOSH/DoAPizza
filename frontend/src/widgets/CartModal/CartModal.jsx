import { useNavigate } from 'react-router-dom';
import { useCart } from '../../entities/cart';
import { useAuth } from '../../features/auth';
import { Button } from '../../shared/ui/Button';
import { formatPrice } from '../../shared/lib/formatPrice';
import styles from './CartModal.module.css';

export function CartModal({ isOpen, onClose }) {
  const { items, totalPrice, updateQuantity, removeItem, getItemPrice } = useCart();
  const { user } = useAuth();
  const navigate = useNavigate();

  const handleCheckout = () => {
    onClose();
    navigate('/checkout');
  };

  const itemCount = items.reduce((sum, i) => sum + i.quantity, 0);

  return (
    <div
      className={`${styles.backdrop} ${isOpen ? styles.backdropOpen : ''}`}
      onClick={onClose}
    >
      <aside
        className={`${styles.drawer} ${isOpen ? styles.drawerOpen : ''}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className={styles.header}>
          <div>
            <h2 className={styles.title}>
              {user?.name ? `Привет, ${user.name}!` : 'Корзина'}
            </h2>
            {itemCount > 0 && (
              <p className={styles.itemCount}>{itemCount} {declOfNum(itemCount, ['товар', 'товара', 'товаров'])}</p>
            )}
          </div>
          <button type="button" className={styles.close} onClick={onClose} aria-label="Закрыть">
            ×
          </button>
        </div>

        <div className={styles.body}>
          {items.length === 0 ? (
            <div className={styles.empty}>
              <div className={styles.emptyIcon}>🛒</div>
              <p className={styles.emptyTitle}>Корзина пуста</p>
              <p className={styles.emptyHint}>Добавьте что-нибудь вкусное из меню</p>
            </div>
          ) : (
            items.map((item) => {
              const price = getItemPrice(item);
              const v = item.variant;
              const sizeName = v?.size || null;

              return (
                <div key={v?.id} className={styles.item}>
                  {v?.dish_image && (
                    <div className={styles.itemImageWrap}>
                      <img src={v.dish_image} alt={v.dish_name} className={styles.itemImage} />
                    </div>
                  )}
                  <div className={styles.itemContent}>
                    <span className={styles.itemName}>
                      {v?.dish_name}
                      {sizeName && <span className={styles.size}> · {sizeName}</span>}
                    </span>
                    <div className={styles.itemBottom}>
                      <div className={styles.quantity}>
                        <button
                          type="button"
                          onClick={() => updateQuantity(v?.id, item.quantity - 1)}
                          aria-label="Уменьшить"
                        >
                          −
                        </button>
                        <span className={styles.quantityValue}>{item.quantity}</span>
                        <button
                          type="button"
                          onClick={() => updateQuantity(v?.id, item.quantity + 1)}
                          aria-label="Увеличить"
                        >
                          +
                        </button>
                      </div>
                      <span className={styles.itemTotal}>{formatPrice(price * item.quantity)}</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className={styles.remove}
                    onClick={() => removeItem(v?.id)}
                    aria-label="Удалить"
                  >
                    ×
                  </button>
                </div>
              );
            })
          )}
        </div>

        {items.length > 0 && (
          <div className={styles.footer}>
            <div className={styles.totalRow}>
              <span className={styles.totalLabel}>Итого</span>
              <span className={styles.totalPrice}>{formatPrice(totalPrice)}</span>
            </div>
            <Button variant="primary" size="lg" fullWidth onClick={handleCheckout}>
              Оформить заказ
            </Button>
          </div>
        )}
      </aside>
    </div>
  );
}

function declOfNum(n, forms) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 19) return forms[2];
  if (mod10 === 1) return forms[0];
  if (mod10 >= 2 && mod10 <= 4) return forms[1];
  return forms[2];
}
