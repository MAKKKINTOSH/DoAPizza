import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';

/**
 * API меню (api_integration.md)
 * GET /api/restaurant/categories/
 * GET /api/restaurant/variants/?category=1&price_min=200&price_max=500
 * GET /api/restaurant/variants/{id}/
 */
export const dishesApi = {
  /**
   * Список категорий
   */
  async getCategories() {
    try {
      const categories = await apiClient.get(ENDPOINTS.RESTAURANT.CATEGORIES);
      return { success: true, categories };
    } catch (error) {
      return {
        success: false,
        message: error.data?.detail || error.message || 'Ошибка при загрузке категорий',
      };
    }
  },

  /**
   * Блюда с вариантами (с опциональной фильтрацией)
   * @param {object} params - { category, calories_min, calories_max, price_min, price_max }
   */
  async getVariants(params = {}) {
    try {
      const qs = new URLSearchParams();
      if (params.category != null) qs.set('category', params.category);
      if (params.calories_min != null) qs.set('calories_min', params.calories_min);
      if (params.calories_max != null) qs.set('calories_max', params.calories_max);
      if (params.price_min != null) qs.set('price_min', params.price_min);
      if (params.price_max != null) qs.set('price_max', params.price_max);
      const query = qs.toString();
      const endpoint = query ? `${ENDPOINTS.RESTAURANT.VARIANTS}?${query}` : ENDPOINTS.RESTAURANT.VARIANTS;
      const data = await apiClient.get(endpoint);
      return { success: true, dishes: Array.isArray(data) ? data : [] };
    } catch (error) {
      return {
        success: false,
        message: error.data?.detail || error.message || 'Ошибка при загрузке меню',
      };
    }
  },

  /**
   * Один вариант блюда
   */
  async getVariantById(id) {
    try {
      const variant = await apiClient.get(ENDPOINTS.RESTAURANT.VARIANT(id));
      return { success: true, variant };
    } catch (error) {
      return {
        success: false,
        message: error.data?.detail || error.message || 'Ошибка при загрузке варианта',
      };
    }
  },
};
