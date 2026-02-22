/**
 * Константы эндпоинтов API
 */
export const ENDPOINTS = {
  // Авторизация
  AUTH: {
    REQUEST_CODE: '/auth/request-code/',
    VERIFY_CODE: '/auth/verify-code/',
    LOGOUT: '/auth/logout/',
    REFRESH: '/auth/refresh/',
    PROFILE: '/auth/profile/',
  },

  // Блюда
  DISHES: {
    LIST: '/dishes/',
    DETAIL: (id) => `/dishes/${id}/`,
    CATEGORIES: '/dishes/categories/',
  },

  // Заказы
  ORDERS: {
    LIST: '/orders/',
    CREATE: '/orders/',
    DETAIL: (id) => `/orders/${id}/`,
    CANCEL: (id) => `/orders/${id}/cancel/`,
    STATUS: (id) => `/orders/${id}/status/`,
  },

  // Профиль
  PROFILE: {
    GET: '/profile/',
    UPDATE: '/profile/',
    ADDRESSES: '/profile/addresses/',
    ADDRESS: (id) => `/profile/addresses/${id}/`,
  },

  // Админка
  ADMIN: {
    ORDERS: '/admin/orders/',
    ORDER_DETAIL: (id) => `/admin/orders/${id}/`,
    UPDATE_ORDER_STATUS: (id) => `/admin/orders/${id}/status/`,
    ASSIGN_COURIER: (id) => `/admin/orders/${id}/assign-courier/`,
    STATISTICS: '/admin/statistics/',
  },
};
