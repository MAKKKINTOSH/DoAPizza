# DoAPizza — Frontend

Сайт доставки пиццы на React + Vite с архитектурой FSD (Feature-Sliced Design).

## Структура проекта (FSD)

```
src/
├── app/           # Инициализация приложения, провайдеры, роутинг
├── pages/         # Страницы
├── widgets/       # Композитные блоки (Header, Footer, Layout)
├── features/      # Фичи (auth, add-to-cart)
├── entities/      # Сущности (dish, cart)
└── shared/        # Общие компоненты и утилиты
```

## Маршруты

- `/` — Меню (главная страница с пиццей и напитками)
- `/cart` — Корзина
- `/checkout` — Оформление заказа
- `/login` — Вход (для клиентов и админов)
- `/admin` — Админ-панель (только для ADMIN)


## Запуск

```bash
npm install
npm run dev
```

Сборка: `npm run build`
