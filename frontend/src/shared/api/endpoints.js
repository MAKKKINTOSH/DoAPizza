/**
 * Эндпоинты API (соответствует api_integration.md)
 */
export const ENDPOINTS = {
  // Авторизация: префикс /api/auth/
  AUTH: {
    REQUEST_CODE: '/auth/request-code/',
    VERIFY_CODE: '/auth/verify-code/',
    TOKEN_REFRESH: '/auth/token/refresh/',
    USER: (id) => `/auth/users/${id}/`,
  },

  // Меню: префикс /api/restaurant/
  RESTAURANT: {
    CATEGORIES: '/restaurant/categories/',
    VARIANTS: '/restaurant/variants/',
    VARIANT: (id) => `/restaurant/variants/${id}/`,
  },

  // Заказы: префикс /api/orders/
  ORDERS: {
    CREATE: '/orders/',
    USER_ORDERS: (userId) => `/orders/users/${userId}/`,
    USER_ORDER: (userId, orderId) => `/orders/users/${userId}/${orderId}/`,
  },
};
