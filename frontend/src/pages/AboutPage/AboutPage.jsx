import { useState, useEffect, useCallback } from 'react';
import photo1 from '../../assets/images/about/photo1.jpg';
import photo2 from '../../assets/images/about/photo2.jpg';
import photo3 from '../../assets/images/about/photo3.jpg';
import styles from './AboutPage.module.css';

export const WORKING_HOURS = 'Ежедневно с 10:00 до 23:00';

const PHOTOS = [
  { src: photo1, alt: 'Интерьер ресторана' },
  { src: photo2, alt: 'Наша пицца' },
  { src: photo3, alt: 'Зал ресторана' },
];

export function AboutPage() {
  const [lightboxIndex, setLightboxIndex] = useState(null);

  const closeLightbox = useCallback(() => setLightboxIndex(null), []);

  const prev = useCallback(() => {
    setLightboxIndex((i) => (i - 1 + PHOTOS.length) % PHOTOS.length);
  }, []);

  const next = useCallback(() => {
    setLightboxIndex((i) => (i + 1) % PHOTOS.length);
  }, []);

  useEffect(() => {
    if (lightboxIndex === null) return;
    const onKey = (e) => {
      if (e.key === 'Escape') closeLightbox();
      if (e.key === 'ArrowLeft') prev();
      if (e.key === 'ArrowRight') next();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [lightboxIndex, closeLightbox, prev, next]);

  useEffect(() => {
    if (lightboxIndex !== null) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => { document.body.style.overflow = prev; };
    }
  }, [lightboxIndex]);

  return (
    <>
      <div className={styles.hero}>
        <h1 className={styles.title}>О нас</h1>
        <p className={styles.lead}>
          DoAPizza — доставка пиццы и любимых блюд. Готовим из свежих продуктов,
          доставляем горячим.
        </p>
      </div>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Кто мы</h2>
        <p className={styles.text}>
          Мы любим пиццу и верим, что хорошая доставка — это быстрый заказ,
          свежие ингредиенты и внимание к каждому клиенту. Наша команда готовит
          пиццу по проверенным рецептам и привозит её к вам.
        </p>
        <p className={styles.text}>
          В меню — классические и авторские пиццы, напитки и десерты. Выбирайте
          на сайте, оформляйте заказ — мы позаботимся об остальном.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Часы работы</h2>
        <p className={styles.text}>{WORKING_HOURS}</p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Контакты и адрес</h2>
        <p className={styles.text}>
          Заказы принимаем на сайте и по телефону.
        </p>
        <div className={styles.mapBlock}>
          <iframe
            className={styles.map}
            src="https://yandex.ru/map-widget/v1/?text=%D0%98%D1%80%D0%BA%D1%83%D1%82%D1%81%D0%BA%2C+%D1%83%D0%BB%D0%B8%D1%86%D0%B0+%D0%9B%D0%B5%D1%80%D0%BC%D0%BE%D0%BD%D1%82%D0%BE%D0%B2%D0%B0%2C+83&z=17"
            title="Карта"
            allowFullScreen
          />
        </div>
        <p className={styles.address}>
          Адрес: г. Иркутск, ул. Лермонтова, 83
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Фотографии</h2>
        <div className={styles.gallery}>
          {PHOTOS.map((photo, idx) => (
            <img
              key={idx}
              className={styles.galleryItem}
              src={photo.src}
              alt={photo.alt}
              onClick={() => setLightboxIndex(idx)}
            />
          ))}
        </div>
      </section>

      {lightboxIndex !== null && (
        <div className={styles.lightboxBackdrop} onClick={closeLightbox}>
          <button className={styles.lightboxClose} onClick={closeLightbox} aria-label="Закрыть">×</button>

          <button
            className={`${styles.lightboxNav} ${styles.lightboxNavPrev}`}
            onClick={(e) => { e.stopPropagation(); prev(); }}
            aria-label="Предыдущее фото"
          >
            ‹
          </button>

          <div className={styles.lightboxImgWrap} onClick={(e) => e.stopPropagation()}>
            <img
              className={styles.lightboxImg}
              src={PHOTOS[lightboxIndex].src}
              alt={PHOTOS[lightboxIndex].alt}
            />
          </div>

          <button
            className={`${styles.lightboxNav} ${styles.lightboxNavNext}`}
            onClick={(e) => { e.stopPropagation(); next(); }}
            aria-label="Следующее фото"
          >
            ›
          </button>

          <div className={styles.lightboxDots}>
            {PHOTOS.map((_, idx) => (
              <span
                key={idx}
                className={`${styles.lightboxDot} ${idx === lightboxIndex ? styles.lightboxDotActive : ''}`}
                onClick={(e) => { e.stopPropagation(); setLightboxIndex(idx); }}
              />
            ))}
          </div>
        </div>
      )}
    </>
  );
}
