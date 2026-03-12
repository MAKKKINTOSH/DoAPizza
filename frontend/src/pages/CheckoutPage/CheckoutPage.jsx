import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../../entities/cart';
import { useAuth } from '../../features/auth';
import { ordersApi } from '../../shared/api';
import { Button } from '../../shared/ui/Button';
import { Input } from '../../shared/ui/Input';
import { formatPrice } from '../../shared/lib/formatPrice';
import styles from './CheckoutPage.module.css';

function normalizePhone(v) {
  const d = String(v).replace(/\D/g, '').replace(/^8/, '7');
  return d.startsWith('7') ? d : '7' + d;
}

export function CheckoutPage() {
  const { items, totalPrice, getItemPrice, clearCart } = useCart();
  const { user, updateUserName } = useAuth();
  const navigate = useNavigate();
  const [address, setAddress] = useState({
    name: user?.name || '',
    address: '',
    phone: user?.phone_number?.replace(/^\+/, '') || '',
    comment: '',
  });
  const [pickup, setPickup] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  useEffect(() => {
    if (user) {
      setAddress((prev) => ({
        ...prev,
        name: prev.name || user.name || '',
        phone: prev.phone || user.phone_number?.replace(/^\+/, '') || '',
      }));
    }
  }, [user?.id]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');
    if (address.name && address.name !== user?.name) {
      updateUserName(address.name);
    }

    const phone = normalizePhone(address.phone);
    if (phone.length < 11) {
      setSubmitError('Введите корректный номер телефона');
      return;
    }

    const orderPayload = {
      phone_number: '+' + phone.replace(/^7/, '7'),
      name: address.name || undefined,
      email: user?.email || undefined,
      address: pickup ? '' : (address.address || '').trim(),
      comment: (address.comment || '').trim() || undefined,
      items: items.map((item) => ({
        dish_variant_id: item.variant?.id,
        quantity: item.quantity,
      })),
    };

    setSubmitting(true);
    const result = await ordersApi.createOrder(orderPayload);
    setSubmitting(false);

    if (result.success) {
      clearCart();
      navigate('/?order=success');
    } else {
      setSubmitError(result.message || 'Не удалось оформить заказ');
    }
  };

  if (items.length === 0) {
    return (
      <div className={styles.empty}>
        <h1 className={styles.title}>Оформление заказа</h1>
        <p className={styles.emptyText}>Корзина пуста. Добавьте блюда из меню.</p>
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
              {items.map((item) => {
                const price = getItemPrice(item);
                const v = item.variant;
                const sizeName = v?.size || '—';
                return (
                  <tr key={v?.id}>
                    <td>{v?.dish_name}</td>
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

        <Input
          label="Телефон"
          type="tel"
          value={address.phone}
          onChange={(v) => setAddress({ ...address, phone: v })}
          placeholder="+7 (999) 123-45-67"
          required
          autoComplete="tel"
        />

        <Input
          label="Комментарий"
          value={address.comment}
          onChange={(v) => setAddress({ ...address, comment: v })}
          placeholder="Дополнительные пожелания"
        />

        {submitError && <p className={styles.submitError}>{submitError}</p>}

        <div className={styles.submitRow}>
          <Button type="submit" variant="primary" size="lg" disabled={submitting}>
            {submitting ? 'Отправка...' : 'Подтвердить заказ'}
          </Button>
        </div>
      </form>
    </>
  );
}
