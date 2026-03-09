# DoAPizza — Backend

REST API бэкенд для приложения доставки пиццы **DoAPizza**, реализованный на Django и Django REST Framework.

---

## Стек технологий

| Технология | Версия | Назначение |
|---|---|---|
| Python | 3.12 | Язык программирования |
| Django | 5.1 | Веб-фреймворк |
| Django REST Framework | 3.15 | REST API |
| djangorestframework-simplejwt | 5.3 | JWT-аутентификация |
| django-filter | 24.3 | Фильтрация запросов |
| django-environ | 0.11 | Переменные окружения |
| drf-spectacular | 0.28 | OpenAPI / Swagger документация |
| PostgreSQL | 17 | База данных |
| pgAdmin 4 | latest | Веб-интерфейс для PostgreSQL |
| Docker / Docker Compose | latest | Контейнеризация |
| Pillow | 11 | Работа с изображениями |

---

## Структура приложения

```
backend/
├── app/                    # Исходный код Django-проекта
│   ├── doapizza/           # Настройки проекта (settings, urls, wsgi)
│   │   ├── .env            # Переменные окружения Django (не коммитится)
│   │   └── .env.example    # Пример переменных окружения Django
│   ├── administration/     # Авторизация и управление пользователями
│   ├── restaurant/         # Ресторан: категории, блюда, варианты
│   ├── orders/             # Заказы и курьеры
│   └── templates/          # Переопределение шаблонов Django Admin
├── media/                  # Загружаемые файлы (изображения блюд)
├── .env                    # Переменные окружения Docker Compose (не коммитится)
├── .env.example            # Пример переменных окружения Docker Compose
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### Приложения

#### `administration` — Авторизация и пользователи
- **Модели:** `User` (номер телефона, имя, email), `DeliveryAddress` (адреса доставки), `AuthCode` (коды авторизации)
- **Авторизация:** через Telegram-бота — пользователь запрашивает код, получает его в Telegram, вводит на клиенте, получает JWT-токены

#### `restaurant` — Меню ресторана
- **Модели:** `Category` (категории блюд), `Dish` (блюда с мягким удалением), `Size` (размеры), `MeasureUnit` (меры измерения), `DishVariant` (варианты блюд с ценой, весом, калорийностью)

#### `orders` — Заказы и курьеры
- **Модели:** `Courier` (с мягким удалением), `Order` (с перечислением статусов), `OrderItem` (элементы заказа)

---

## API Endpoints

Полная спецификация с примерами запросов и ответов — в файле [api_integration.md](api_integration.md).

### Авторизация (`/api/auth/`)

| Метод | URL | Описание |
|---|---|---|
| POST | `/api/auth/request-code/` | Запросить код авторизации |
| POST | `/api/auth/verify-code/` | Верифицировать код, получить JWT |
| POST | `/api/auth/token/refresh/` | Обновить access-токен |
| POST | `/api/auth/users/` | Создать пользователя |
| GET | `/api/auth/users/{id}/` | Получить данные пользователя (с адресами) |

### Ресторан (`/api/restaurant/`)

| Метод | URL | Описание |
|---|---|---|
| GET | `/api/restaurant/categories/` | Список категорий |
| GET | `/api/restaurant/variants/` | Список блюд с вариантами (с фильтрами) |
| GET | `/api/restaurant/variants/{id}/` | Один вариант блюда по id |

### Заказы (`/api/orders/`)

| Метод | URL | Описание |
|---|---|---|
| POST | `/api/orders/` | Создать заказ |
| GET | `/api/orders/users/{user_id}/` | Список заказов пользователя (с фильтрами) |
| GET | `/api/orders/users/{user_id}/{id}/` | Заказ пользователя по id |

### Документация API

| URL | Описание |
|---|---|
| `/api/schema/` | OpenAPI схема (JSON/YAML) |
| `/api/schema/swagger/` | Swagger UI |
| `/api/schema/redoc/` | ReDoc UI |

---

## Развертывание

### Предварительные требования

- Docker >= 24
- Docker Compose >= 2.20

### Шаги

1. **Перейдите в директорию бэкенда:**
   ```bash
   cd backend
   ```

2. **Создайте файлы переменных окружения:**

   Для Docker Compose (PostgreSQL, pgAdmin):
   ```bash
   cp .env.example .env
   ```

   Для Django (настройки приложения):
   ```bash
   cp app/doapizza/.env.example app/doapizza/.env
   ```

   При необходимости отредактируйте оба файла (особенно `SECRET_KEY` для продакшена).

3. **Запустите все сервисы:**
   ```bash
   docker compose up -d --build
   ```
   Docker Compose автоматически выполнит сбор статики и запустит сервер.

4. **Создайте суперпользователя для Django Admin:**
   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```

5. **Сервисы доступны по адресам:**
   - Django API: [http://localhost:8000](http://localhost:8000)
   - Django Admin: [http://localhost:8000/admin](http://localhost:8000/admin)
   - Swagger UI: [http://localhost:8000/api/schema/swagger/](http://localhost:8000/api/schema/swagger/)
   - ReDoc: [http://localhost:8000/api/schema/redoc/](http://localhost:8000/api/schema/redoc/)
   - pgAdmin: [http://localhost:5050](http://localhost:5050)

### Подключение pgAdmin к базе данных

В pgAdmin добавьте новый сервер:
- **Host:** `db`
- **Port:** `5432`
- **Database:** значение `POSTGRES_DB` из `.env`
- **Username:** значение `POSTGRES_USER` из `.env`
- **Password:** значение `POSTGRES_PASSWORD` из `.env`

### Остановка

```bash
docker compose down
```

С удалением данных:
```bash
docker compose down -v
```
