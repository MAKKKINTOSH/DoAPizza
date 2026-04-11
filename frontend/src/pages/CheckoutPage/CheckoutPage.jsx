import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../../entities/cart';
import { useAuth } from '../../features/auth';
import { ordersApi } from '../../shared/api';
import { Button } from '../../shared/ui/Button';
import { Input } from '../../shared/ui/Input';
import { useToast } from '../../shared/ui/Toast';
import { formatPrice } from '../../shared/lib/formatPrice';
import styles from './CheckoutPage.module.css';

const DADATA_TOKEN = 'd9b6c145105eb8bda3761b248201ea5b07a1c8bf';

async function fetchAddressSuggestions(query) {
  if (!query || query.trim().length < 3) return [];
  try {
    const res = await fetch('https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': `Token ${DADATA_TOKEN}`,
      },
      body: JSON.stringify({ query: query.trim(), count: 5, locations: [{ country: 'Россия' }] }),
    });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.suggestions || []).map((s) => s.value);
  } catch {
    return [];
  }
}

// Разрешённые символы для адреса: кириллица, латиница, цифры, пробел и знаки пунктуации адресов
const ADDRESS_ALLOWED_RE = /^[а-яёА-ЯЁa-zA-Z0-9\s.,\-/()\u00C0-\u024F]+$/;

function validateAddress(v) {
  const t = (v || '').trim();
  if (t.length < 5) return 'Введите адрес доставки';
  if (!ADDRESS_ALLOWED_RE.test(t)) return 'Адрес содержит недопустимые символы';
  if (!/[а-яёА-ЯЁ]/.test(t)) return 'Укажите название улицы';
  if (!/\d/.test(t)) return 'Укажите номер дома';
  return '';
}

function AddressInput({ value, onChange, required, externalError }) {
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const [touched, setTouched] = useState(false);
  const debounceRef = useRef(null);
  const wrapRef = useRef(null);

  const error = touched ? validateAddress(value) : (externalError || '');

  const handleChange = useCallback((v) => {
    onChange(v);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      const list = await fetchAddressSuggestions(v);
      setSuggestions(list);
      setOpen(list.length > 0);
    }, 350);
  }, [onChange]);

  const handleSelect = (suggestion) => {
    onChange(suggestion);
    setSuggestions([]);
    setOpen(false);
    setTouched(true);
  };

  useEffect(() => {
    const onOutside = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onOutside);
    return () => document.removeEventListener('mousedown', onOutside);
  }, []);

  return (
    <div ref={wrapRef} className={styles.addressWrap}>
      <Input
        label="Адрес доставки"
        value={value}
        onChange={handleChange}
        onBlur={() => setTouched(true)}
        placeholder="Улица, дом, квартира"
        required={required}
        autoComplete="off"
      />
      {error && <p className={styles.fieldError}>{error}</p>}
      {open && suggestions.length > 0 && (
        <ul className={styles.suggestions}>
          {suggestions.map((s, i) => (
            <li
              key={i}
              className={styles.suggestionItem}
              onMouseDown={() => handleSelect(s)}
            >
              {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function normalizePhone(v) {
  const d = String(v).replace(/\D/g, '').replace(/^8/, '7');
  return d.startsWith('7') ? d : '7' + d;
}

function formatPhoneDisplay(digits) {
  let d = (digits || '').replace(/\D/g, '').replace(/^8/, '7').slice(0, 11);
  if (d && !d.startsWith('7')) d = '7' + d;
  const p1 = d.slice(1, 4);
  const p2 = d.slice(4, 7);
  const p3 = d.slice(7, 9);
  const p4 = d.slice(9, 11);
  if (!d || d === '7') return '+7 ';
  let out = `+7 (${p1}`;
  if (p2) out += `) ${p2}`;
  if (p3) out += ` - ${p3}`;
  if (p4) out += ` - ${p4}`;
  return out.replace(/\s*-\s*$/g, '').trim();
}

function parsePhoneInput(value) {
  let digits = value.replace(/\D/g, '').replace(/^8/, '7').slice(0, 11);
  if (digits && !digits.startsWith('7')) digits = '7' + digits;
  return digits;
}

export function CheckoutPage() {
  const { items, totalPrice, getItemPrice, clearCart } = useCart();
  const { user, updateUserName } = useAuth();
  const { showToast } = useToast();
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
  const [addressError, setAddressError] = useState('');

  const [bonusBalance, setBonusBalance] = useState(0);
  const [bonusToUse, setBonusToUse] = useState(0);
  const [bonusInput, setBonusInput] = useState('');

  useEffect(() => {
    if (user) {
      setAddress((prev) => ({
        ...prev,
        name: prev.name || user.name || '',
        phone: prev.phone || user.phone_number?.replace(/^\+/, '') || '',
      }));
    }
  }, [user?.id]);

  useEffect(() => {
    if (!user?.id) return;
    ordersApi.getUserBonus(user.id).then((result) => {
      if (result.success) setBonusBalance(Math.floor(result.balance));
    });
  }, [user?.id]);

  const handleBonusInput = (raw) => {
    const digits = raw.replace(/\D/g, '');
    setBonusInput(digits);
    const val = parseInt(digits, 10) || 0;
    setBonusToUse(Math.min(val, bonusBalance, Math.floor(totalPrice)));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError('');

    if (!pickup) {
      const addrErr = validateAddress(address.address);
      setAddressError(addrErr);
      if (addrErr) return;
    } else {
      setAddressError('');
    }

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
      bonus_points: bonusToUse > 0 ? bonusToUse : undefined,
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
      showToast('Заказ успешно оформлен!');
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
          <div className={styles.tableScroll}>
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
          </div>
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
          <AddressInput
            value={address.address}
            onChange={(v) => { setAddressError(''); setAddress({ ...address, address: v }); }}
            required
            externalError={addressError}
          />
        )}

        <Input
          label="Телефон"
          type="tel"
          value={formatPhoneDisplay(address.phone)}
          onChange={(v) => setAddress({ ...address, phone: parsePhoneInput(v) })}
          placeholder="+7 (___) ___ - __ - __"
          required
          autoComplete="tel"
        />

        <Input
          label="Комментарий"
          value={address.comment}
          onChange={(v) => setAddress({ ...address, comment: v })}
          placeholder="Дополнительные пожелания"
        />

        {bonusBalance > 0 && (
          <div className={styles.bonusSection}>
            <div className={styles.bonusSectionHeader}>
              <span className={styles.bonusLabel}>Бонусы</span>
              <span className={styles.bonusAvail}>Доступно: {bonusBalance} бонусов</span>
            </div>
            <div className={styles.bonusRow}>
              <input
                type="number"
                min={0}
                max={Math.min(bonusBalance, Math.floor(totalPrice))}
                value={bonusInput}
                onChange={(e) => handleBonusInput(e.target.value)}
                placeholder="0"
                className={styles.bonusInput}
              />
              <button
                type="button"
                className={styles.bonusMax}
                onClick={() => handleBonusInput(String(Math.min(bonusBalance, Math.floor(totalPrice))))}
              >
                Списать всё
              </button>
            </div>
            {bonusToUse > 0 && (
              <p className={styles.bonusHint}>
                Скидка: −{bonusToUse} ₽ · к оплате: {formatPrice(totalPrice - bonusToUse)}
              </p>
            )}
          </div>
        )}

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
