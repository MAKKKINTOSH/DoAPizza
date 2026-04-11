import { useState, useEffect } from 'react';
import { useAuth } from '../../features/auth';
import { Input } from '../../shared/ui/Input';
import { Button } from '../../shared/ui/Button';
import { ordersApi } from '../../shared/api';
import styles from './ProfilePage.module.css';

function formatDate(iso) {
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function OrderCard({ order }) {
  const subtotal = order.items.reduce(
    (sum, item) => sum + parseFloat(item.dish_variant.price) * item.quantity,
    0,
  );
  const discount = parseFloat(order.bonus_discount) || 0;
  const total = subtotal - discount;

  return (
    <div className={styles.orderCard}>
      <div className={styles.orderHeader}>
        <span className={styles.orderId}>Заказ №{order.id}</span>
        <span className={styles.orderStatus}>{order.status_display}</span>
      </div>
      <div className={styles.orderMeta}>
        <span>{formatDate(order.started_at)}</span>
        <span>{order.is_pickup ? 'Самовывоз' : order.address}</span>
      </div>
      <ul className={styles.orderItems}>
        {order.items.map((item) => (
          <li key={item.id} className={styles.orderItem}>
            <span>{item.dish_variant.dish_name} ({item.dish_variant.size.label})</span>
            <span>{item.quantity} × {parseFloat(item.dish_variant.price).toFixed(0)} ₽</span>
          </li>
        ))}
      </ul>
      {discount > 0 && (
        <div className={styles.orderDiscount}>Бонусы: −{discount.toFixed(0)} ₽</div>
      )}
      <div className={styles.orderTotal}>Итого: {total.toFixed(0)} ₽</div>
    </div>
  );
}

export function ProfilePage() {
  const { user, updateUserName } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const [orders, setOrders] = useState([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState(null);

  const [bonus, setBonus] = useState(null);
  const [bonusLoading, setBonusLoading] = useState(false);

  useEffect(() => {
    setName(user?.name || '');
  }, [user?.name]);

  useEffect(() => {
    if (!user?.id) return;
    setOrdersLoading(true);
    ordersApi.getUserOrders(user.id).then((result) => {
      if (result.success) {
        setOrders(result.orders);
      } else {
        setOrdersError(result.message);
      }
      setOrdersLoading(false);
    });
  }, [user?.id]);

  useEffect(() => {
    if (!user?.id) return;
    setBonusLoading(true);
    ordersApi.getUserBonus(user.id).then((result) => {
      if (result.success) setBonus(result);
      setBonusLoading(false);
    });
  }, [user?.id]);

  const handleSave = () => {
    if (name.trim()) {
      setSaving(true);
      updateUserName(name.trim());
      setTimeout(() => {
        setSaving(false);
        setIsEditing(false);
      }, 300);
    }
  };

  const handleCancel = () => {
    setName(user?.name || '');
    setIsEditing(false);
  };

  return (
    <div className={styles.wrapper}>
      <h1 className={styles.title}>Профиль</h1>
      <p className={styles.lead}>
        Здесь собраны история заказов и бонусная программа.
      </p>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Как к вам обращаться</h2>
        {isEditing ? (
          <div className={styles.nameEdit}>
            <Input
              label="Ваше имя"
              value={name}
              onChange={setName}
              placeholder="Введите ваше имя"
              autoComplete="name"
            />
            <div className={styles.nameActions}>
              <Button
                variant="primary"
                size="md"
                onClick={handleSave}
                disabled={saving || !name.trim()}
              >
                Сохранить
              </Button>
              <Button
                variant="secondary"
                size="md"
                onClick={handleCancel}
                disabled={saving}
              >
                Отмена
              </Button>
            </div>
          </div>
        ) : (
          <div className={styles.nameDisplay}>
            <p className={styles.nameValue}>
              {user?.name || 'Имя не указано'}
            </p>
            <Button
              variant="secondary"
              size="md"
              onClick={() => setIsEditing(true)}
            >
              {user?.name ? 'Изменить' : 'Указать имя'}
            </Button>
          </div>
        )}
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>История заказов</h2>
        {ordersLoading && <p className={styles.text}>Загрузка...</p>}
        {ordersError && <p className={styles.text}>{ordersError}</p>}
        {!ordersLoading && !ordersError && orders.length === 0 && (
          <div className={styles.placeholder}>
            <p>История заказов пока пуста.</p>
            <p>Сделайте первый заказ, и он появится здесь.</p>
          </div>
        )}
        {!ordersLoading && orders.length > 0 && (
          <div className={styles.orderList}>
            {orders.map((order) => (
              <OrderCard key={order.id} order={order} />
            ))}
          </div>
        )}
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Бонусы</h2>
        <div className={styles.bonusRules}>
          <p>За каждый доставленный заказ начисляется <strong>5%</strong> от его суммы в виде бонусов.</p>
          <p>Бонусы можно списать при оформлении следующего заказа — 1 бонус = 1 ₽.</p>
        </div>
        {bonusLoading && <p className={styles.text}>Загрузка...</p>}
        {!bonusLoading && bonus !== null && (
          <>
            <div className={styles.bonusBalance}>
              Баланс: <strong>{Math.floor(bonus.balance)} бонусов</strong>
            </div>
            {bonus.transactions.length > 0 ? (
              <ul className={styles.bonusList}>
                {bonus.transactions.map((tx) => {
                  const earned = tx.transaction_type === 'earned';
                  return (
                    <li key={tx.id} className={styles.bonusItem}>
                      <span className={earned ? styles.bonusEarned : styles.bonusRedeemed}>
                        {earned ? '+' : ''}{parseFloat(tx.amount).toFixed(0)} бонусов
                      </span>
                      <span className={styles.bonusMeta}>
                        {earned ? 'Начислено' : 'Списано'} · заказ №{tx.order} · {formatDate(tx.created_at)}
                      </span>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <div className={styles.placeholder}>
                <p>Бонусов пока нет.</p>
                <p>Оформляйте заказы, и бонусы начнут накапливаться.</p>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
