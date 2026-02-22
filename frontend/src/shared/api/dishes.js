import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';

/**
 * API для работы с блюдами
 */
export const dishesApi = {
  /**
   * Получить список блюд
   * @param {object} params - Параметры запроса (category, search, page, page_size)
   * @returns {Promise<{success: boolean, dishes?: array, count?: number}>}
   */
  async getDishes(params = {}) {
    try {
      const queryParams = new URLSearchParams();
      if (params.category) queryParams.append('category', params.category);
      if (params.search) queryParams.append('search', params.search);
      if (params.page) queryParams.append('page', params.page);
      if (params.page_size) queryParams.append('page_size', params.page_size);

      const endpoint = `${ENDPOINTS.DISHES.LIST}${queryParams.toString() ? `?${queryParams}` : ''}`;
      const response = await apiClient.get(endpoint);
      
      return {
        success: true,
        dishes: response.results || response,
        count: response.count,
        next: response.next,
        previous: response.previous,
      };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при загрузке блюд',
      };
    }
  },

  /**
   * Получить информацию о блюде по ID
   * @param {number|string} id - ID блюда
   * @returns {Promise<{success: boolean, dish?: object}>}
   */
  async getDishById(id) {
    try {
      const dish = await apiClient.get(ENDPOINTS.DISHES.DETAIL(id));
      return { success: true, dish };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при загрузке блюда',
      };
    }
  },

  /**
   * Получить список категорий блюд
   * @returns {Promise<{success: boolean, categories?: array}>}
   */
  async getCategories() {
    try {
      const categories = await apiClient.get(ENDPOINTS.DISHES.CATEGORIES);
      return { success: true, categories };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при загрузке категорий',
      };
    }
  },
};
