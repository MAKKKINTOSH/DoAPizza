export const APP_NAME = 'DoAPizza';

// Базовый URL API (Django backend на порту 8000)
// Можно переопределить через переменную окружения VITE_API_URL в .env файле
export const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

// Ссылка на Django admin
export const DJANGO_ADMIN_URL = 'http://127.0.0.1:8000/admin/';
