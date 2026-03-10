import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';

/**
 * API заказов (api_integration.md)
 */
export const ordersApi = {
  /**
   * Создать заказ
   * @param {object} data - { phone_number, name?, email?, address?, comment?, items: [{ dish_variant_id, quantity }] }
   */
  async createOrder(data) {
    try {
      const order = await apiClient.post(ENDPOINTS.ORDERS.CREATE, data);
      return { success: true, order };
    } catch (error) {
      const msg = Array.isArray(error.data?.items)
        ? error.data.items[0]
        : error.data?.detail
        ? (typeof error.data.detail === 'string' ? error.data.detail : JSON.stringify(error.data.detail))
        : error.message;
      return {
        success: false,
        message: msg || 'Ошибка при создании заказа',
        errors: error.data,
      };
    }
  },

  /**
   * Заказы пользователя
   * @param {number} userId
   * @param {object} params - { status, started_at_from, started_at_to }
   */
  async getUserOrders(userId, params = {}) {
    try {
      const qs = new URLSearchParams(params);
      const query = qs.toString();
      const endpoint = query
        ? `${ENDPOINTS.ORDERS.USER_ORDERS(userId)}?${query}`
        : ENDPOINTS.ORDERS.USER_ORDERS(userId);
      const orders = await apiClient.get(endpoint);
      return { success: true, orders: Array.isArray(orders) ? orders : [] };
    } catch (error) {
      return {
        success: false,
        message: error.data?.detail || error.message || 'Ошибка при загрузке заказов',
      };
    }
  },

  /**
   * Один заказ пользователя
   */
  async getUserOrder(userId, orderId) {
    try {
      const order = await apiClient.get(ENDPOINTS.ORDERS.USER_ORDER(userId, orderId));
      return { success: true, order };
    } catch (error) {
      return {
        success: false,
        message: error.data?.detail || error.message || 'Ошибка при загрузке заказа',
      };
    }
  },
};
