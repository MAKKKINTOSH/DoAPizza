import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';

/**
 * API для работы с заказами
 */
export const ordersApi = {
  /**
   * Получить список заказов пользователя
   * @param {object} params - Параметры запроса (status, page, page_size)
   * @returns {Promise<{success: boolean, orders?: array, count?: number}>}
   */
  async getOrders(params = {}) {
    try {
      const queryParams = new URLSearchParams();
      if (params.status) queryParams.append('status', params.status);
      if (params.page) queryParams.append('page', params.page);
      if (params.page_size) queryParams.append('page_size', params.page_size);

      const endpoint = `${ENDPOINTS.ORDERS.LIST}${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await apiClient.get(endpoint);
      
      return {
        success: true,
        orders: response.results || response,
        count: response.count,
        next: response.next,
        previous: response.previous,
      };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при загрузке заказов',
      };
    }
  },

  /**
   * Создать новый заказ
   * @param {object} orderData - Данные заказа
   * @param {array} orderData.items - Массив позиций заказа [{dish_id, size_id, quantity}]
   * @param {string} orderData.address - Адрес доставки
   * @param {string} orderData.phone - Телефон для связи
   * @param {string} orderData.comment - Комментарий к заказу (опционально)
   * @returns {Promise<{success: boolean, order?: object, message?: string}>}
   */
  async createOrder(orderData) {
    try {
      const order = await apiClient.post(ENDPOINTS.ORDERS.CREATE, orderData);
      return { success: true, order };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при создании заказа',
        errors: error.data?.errors,
      };
    }
  },

  /**
   * Получить информацию о заказе по ID
   * @param {number|string} id - ID заказа
   * @returns {Promise<{success: boolean, order?: object}>}
   */
  async getOrderById(id) {
    try {
      const order = await apiClient.get(ENDPOINTS.ORDERS.DETAIL(id));
      return { success: true, order };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при загрузке заказа',
      };
    }
  },

  /**
   * Отменить заказ
   * @param {number|string} id - ID заказа
   * @returns {Promise<{success: boolean, message?: string}>}
   */
  async cancelOrder(id) {
    try {
      await apiClient.post(ENDPOINTS.ORDERS.CANCEL(id));
      return { success: true };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при отмене заказа',
      };
    }
  },

  /**
   * Получить статус заказа
   * @param {number|string} id - ID заказа
   * @returns {Promise<{success: boolean, status?: string}>}
   */
  async getOrderStatus(id) {
    try {
      const response = await apiClient.get(ENDPOINTS.ORDERS.STATUS(id));
      return { success: true, status: response.status };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при получении статуса',
      };
    }
  },
};

/**
 * API для администратора (работа с заказами)
 */
export const adminOrdersApi = {
  /**
   * Получить список всех заказов (для админа)
   * @param {object} params - Параметры запроса (status, courier_id, page, page_size)
   * @returns {Promise<{success: boolean, orders?: array, count?: number}>}
   */
  async getOrders(params = {}) {
    try {
      const queryParams = new URLSearchParams();
      if (params.status) queryParams.append('status', params.status);
      if (params.courier_id) queryParams.append('courier_id', params.courier_id);
      if (params.page) queryParams.append('page', params.page);
      if (params.page_size) queryParams.append('page_size', params.page_size);

      const endpoint = `${ENDPOINTS.ADMIN.ORDERS}${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await apiClient.get(endpoint);
      
      return {
        success: true,
        orders: response.results || response,
        count: response.count,
        next: response.next,
        previous: response.previous,
      };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при загрузке заказов',
      };
    }
  },

  /**
   * Получить информацию о заказе (для админа)
   * @param {number|string} id - ID заказа
   * @returns {Promise<{success: boolean, order?: object}>}
   */
  async getOrderById(id) {
    try {
      const order = await apiClient.get(ENDPOINTS.ADMIN.ORDER_DETAIL(id));
      return { success: true, order };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при загрузке заказа',
      };
    }
  },

  /**
   * Обновить статус заказа
   * @param {number|string} id - ID заказа
   * @param {string} status - Новый статус
   * @returns {Promise<{success: boolean, order?: object}>}
   */
  async updateOrderStatus(id, status) {
    try {
      const order = await apiClient.patch(ENDPOINTS.ADMIN.UPDATE_ORDER_STATUS(id), { status });
      return { success: true, order };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при обновлении статуса',
      };
    }
  },

  /**
   * Назначить курьера на заказ
   * @param {number|string} orderId - ID заказа
   * @param {number|string} courierId - ID курьера
   * @returns {Promise<{success: boolean, order?: object}>}
   */
  async assignCourier(orderId, courierId) {
    try {
      const order = await apiClient.post(ENDPOINTS.ADMIN.ASSIGN_COURIER(orderId), { courier_id: courierId });
      return { success: true, order };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при назначении курьера',
      };
    }
  },

  /**
   * Получить статистику заказов
   * @param {object} params - Параметры (date_from, date_to)
   * @returns {Promise<{success: boolean, statistics?: object}>}
   */
  async getStatistics(params = {}) {
    try {
      const queryParams = new URLSearchParams();
      if (params.date_from) queryParams.append('date_from', params.date_from);
      if (params.date_to) queryParams.append('date_to', params.date_to);

      const endpoint = `${ENDPOINTS.ADMIN.STATISTICS}${queryParams.toString() ? `?${queryParams}` : ''}`;
      const statistics = await apiClient.get(endpoint);
      return { success: true, statistics };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при получении статистики',
      };
    }
  },
};
