import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';

const TOKEN_KEY = 'doapizza_token';
const REFRESH_KEY = 'doapizza_refresh';

/**
 * API авторизации (api_integration.md)
 */
export const authApi = {
  /**
   * Запросить код для входа
   * @param {string} phoneNumber - Номер в формате +79001234567
   * @returns {Promise<{success: boolean, message?: string}>}
   */
  async requestCode(phoneNumber) {
    try {
      await apiClient.post(ENDPOINTS.AUTH.REQUEST_CODE, { phone_number: phoneNumber });
      return { success: true };
    } catch (error) {
      const msg = error.data?.phone_number?.[0] || error.data?.detail || error.message;
      return { success: false, message: msg || 'Ошибка при запросе кода' };
    }
  },

  /**
   * Проверить код и получить JWT
   * @param {string} phoneNumber - +79001234567
   * @param {string} code - 6-значный код
   * @returns {Promise<{success: boolean, user?: object, message?: string}>}
   */
  async verifyCode(phoneNumber, code) {
    try {
      const response = await apiClient.post(ENDPOINTS.AUTH.VERIFY_CODE, {
        phone_number: phoneNumber,
        code: String(code),
      });
      if (response.access) {
        localStorage.setItem(TOKEN_KEY, response.access);
      }
      if (response.refresh) {
        localStorage.setItem(REFRESH_KEY, response.refresh);
      }
      return {
        success: true,
        user: response.user,
      };
    } catch (error) {
      const msg = error.data?.detail || error.message || 'Неверный или истёкший код.';
      return { success: false, message: msg };
    }
  },

  /**
   * Обновить access-токен
   */
  async refreshToken() {
    const refresh = localStorage.getItem(REFRESH_KEY);
    if (!refresh) return { success: false };
    try {
      const response = await apiClient.post(ENDPOINTS.AUTH.TOKEN_REFRESH, { refresh });
      if (response.access) {
        localStorage.setItem(TOKEN_KEY, response.access);
        return { success: true, access: response.access };
      }
      return { success: false };
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_KEY);
      return { success: false };
    }
  },

  logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },

  /**
   * Получить профиль пользователя
   * @param {number} userId
   */
  async getUser(userId) {
    try {
      const user = await apiClient.get(ENDPOINTS.AUTH.USER(userId));
      return { success: true, user };
    } catch (error) {
      return {
        success: false,
        message: error.data?.detail || error.message || 'Ошибка при загрузке профиля',
      };
    }
  },
};
