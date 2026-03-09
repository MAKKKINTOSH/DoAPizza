import { useState, useEffect } from 'react';
import { useAuth } from '../../features/auth';
import { Input } from '../../shared/ui/Input';
import { Button } from '../../shared/ui/Button';
import styles from './ProfilePage.module.css';

export function ProfilePage() {
  const { user, updateUserName } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setName(user?.name || '');
  }, [user?.name]);

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
        Здесь собраны ваши сохранённые адреса, история заказов и бонусная программа.
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
        <h2 className={styles.sectionTitle}>Мои адреса</h2>
        <p className={styles.text}>
          Здесь вы сможете сохранять любимые адреса доставки, чтобы заказывать ещё быстрее.
        </p>
        <div className={styles.placeholder}>
          <p>Список адресов пока пуст.</p>
          <p>Добавьте первый адрес при оформлении заказа.</p>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>История заказов</h2>
        <p className={styles.text}>
          Здесь появится список ваших прошлых заказов с деталями, адресами и статусами.
        </p>
        <div className={styles.placeholder}>
          <p>История заказов пока пуста.</p>
          <p>Сделайте первый заказ, и он появится здесь.</p>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Бонусы</h2>
        <p className={styles.text}>
          Здесь будет отображаться ваш бонусный баланс, история начислений и правила программы лояльности.
        </p>
        <div className={styles.placeholder}>
          <p>Пока бонусов нет.</p>
          <p>Оформляйте заказы, и бонусы начнут накапливаться.</p>
        </div>
      </section>
    </div>
  );
}

