import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';

/**
 * API для авторизации
 */
export const authApi = {
  /**
   * Запросить код для входа
   * @param {string} phone - Номер телефона (10 цифр без +7)
   * @returns {Promise<{success: boolean, message?: string}>}
   */
  async requestCode(phone) {
    try {
      const response = await apiClient.post(ENDPOINTS.AUTH.REQUEST_CODE, { phone });
      return { success: true, ...response };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при запросе кода',
      };
    }
  },

  /**
   * Проверить код и авторизоваться
   * @param {string} phone - Номер телефона (10 цифр без +7)
   * @param {string} code - Код подтверждения
   * @returns {Promise<{success: boolean, token?: string, user?: object, message?: string}>}
   */
  async verifyCode(phone, code) {
    try {
      const response = await apiClient.post(ENDPOINTS.AUTH.VERIFY_CODE, { phone, code });
      
      // Сохраняем токен, если он пришел в ответе
      if (response.token) {
        localStorage.setItem('doapizza_token', response.token);
      }
      
      return {
        success: true,
        token: response.token,
        user: response.user,
        role: response.user?.role,
      };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Неверный код. Проверьте и попробуйте снова.',
      };
    }
  },

  /**
   * Выйти из системы
   * @returns {Promise<{success: boolean}>}
   */
  async logout() {
    try {
      await apiClient.post(ENDPOINTS.AUTH.LOGOUT);
      localStorage.removeItem('doapizza_token');
      return { success: true };
    } catch (error) {
      // Удаляем токен даже при ошибке
      localStorage.removeItem('doapizza_token');
      return { success: true };
    }
  },

  /**
   * Обновить токен
   * @returns {Promise<{success: boolean, token?: string}>}
   */
  async refreshToken() {
    try {
      const response = await apiClient.post(ENDPOINTS.AUTH.REFRESH);
      if (response.token) {
        localStorage.setItem('doapizza_token', response.token);
      }
      return { success: true, token: response.token };
    } catch (error) {
      localStorage.removeItem('doapizza_token');
      return { success: false };
    }
  },

  /**
   * Получить профиль текущего пользователя
   * @returns {Promise<{success: boolean, user?: object}>}
   */
  async getProfile() {
    try {
      const user = await apiClient.get(ENDPOINTS.AUTH.PROFILE);
      return { success: true, user };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при получении профиля',
      };
    }
  },
};
