import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../../entities/cart';
import { useAuth } from '../../features/auth';
import { PIZZA_SIZES } from '../../entities/dish';
import { Button } from '../../shared/ui/Button';
import { Input } from '../../shared/ui/Input';
import { formatPrice } from '../../shared/lib/formatPrice';
import styles from './CheckoutPage.module.css';

export function CheckoutPage() {
  const { items, totalPrice, getItemPrice, clearCart } = useCart();
  const { user, updateUserName } = useAuth();
  const navigate = useNavigate();
  const [address, setAddress] = useState({
    name: user?.name || '',
    address: '',
    phone: '',
    comment: '',
    persons: 1,
  });
  const [pickup, setPickup] = useState(false);

  // Обновляем имя при изменении пользователя
  useEffect(() => {
    if (user?.name && !address.name) {
      setAddress((prev) => ({ ...prev, name: user.name }));
    }
  }, [user?.name]);

  const handleSubmit = (e) => {
    e.preventDefault();
    // Сохраняем имя в профиль, если оно было изменено
    if (address.name && address.name !== user?.name) {
      updateUserName(address.name);
    }
    clearCart();
    navigate('/?order=success');
  };

  if (items.length === 0) {
    return (
      <div className={styles.empty}>
        <h1 className={styles.title}>Оформление заказа</h1>
        <p className={styles.emptyText}>Тут пока ничего нет, корзина пуста.</p>
      </div>
    );
  }

  return (
    <>
      <h1 className={styles.title}>Оформление заказа</h1>

      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.tableSection}>
          <h2 className={styles.tableTitle}>Состав заказа</h2>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Название</th>
                <th>Размер</th>
                <th>Кол-во</th>
                <th>Цена</th>
                <th>Сумма</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => {
                const price = getItemPrice(item);
                const sizeName =
                  item.sizeId && item.dish.hasSizes
                    ? PIZZA_SIZES.find((s) => s.id === item.sizeId)?.name
                    : '—';

                return (
                  <tr key={`${item.dish.id}-${item.sizeId || 'x'}-${idx}`}>
                    <td>{item.dish.name}</td>
                    <td>{sizeName}</td>
                    <td>{item.quantity}</td>
                    <td>{formatPrice(price)}</td>
                    <td className={styles.cellSum}>{formatPrice(price * item.quantity)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className={styles.tableTotal}>
            Итого: <strong>{formatPrice(totalPrice)}</strong>
          </div>
        </div>

        <Input
          label="Как к вам обращаться"
          value={address.name}
          onChange={(v) => setAddress({ ...address, name: v })}
          placeholder="Ваше имя"
          autoComplete="name"
        />

        <label className={styles.checkbox}>
          <input
            type="checkbox"
            checked={pickup}
            onChange={(e) => setPickup(e.target.checked)}
          />
          Самовывоз
        </label>

        {!pickup && (
          <Input
            label="Адрес доставки"
            value={address.address}
            onChange={(v) => setAddress({ ...address, address: v })}
            placeholder="Улица, дом, квартира"
            required
            autoComplete="street-address"
          />
        )}

        <div className={styles.fieldsRow}>
          <Input
            label="Телефон"
            type="tel"
            value={address.phone}
            onChange={(v) => setAddress({ ...address, phone: v })}
            placeholder="999 123 45 67"
            required
            autoComplete="tel"
          />
          <Input
            label="Количество персон"
            type="number"
            min={1}
            max={20}
            value={address.persons}
            onChange={(v) => setAddress({ ...address, persons: Number(v) || 1 })}
          />
        </div>

        <Input
          label="Комментарий"
          value={address.comment}
          onChange={(v) => setAddress({ ...address, comment: v })}
          placeholder="Дополнительные пожелания"
        />

        <div className={styles.submitRow}>
          <Button type="submit" variant="primary" size="lg">
            Подтвердить заказ
          </Button>
        </div>
      </form>
    </>
  );
}
