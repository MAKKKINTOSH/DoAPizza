import { apiClient } from './client';
import { ENDPOINTS } from './endpoints';

/**
 * API для работы с профилем пользователя
 */
export const profileApi = {
  /**
   * Получить профиль пользователя
   * @returns {Promise<{success: boolean, profile?: object}>}
   */
  async getProfile() {
    try {
      const profile = await apiClient.get(ENDPOINTS.PROFILE.GET);
      return { success: true, profile };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при загрузке профиля',
      };
    }
  },

  /**
   * Обновить профиль пользователя
   * @param {object} profileData - Данные профиля (name, email, phone и т.д.)
   * @returns {Promise<{success: boolean, profile?: object}>}
   */
  async updateProfile(profileData) {
    try {
      const profile = await apiClient.patch(ENDPOINTS.PROFILE.UPDATE, profileData);
      return { success: true, profile };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при обновлении профиля',
        errors: error.data?.errors,
      };
    }
  },

  /**
   * Получить список адресов пользователя
   * @returns {Promise<{success: boolean, addresses?: array}>}
   */
  async getAddresses() {
    try {
      const addresses = await apiClient.get(ENDPOINTS.PROFILE.ADDRESSES);
      return { success: true, addresses };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при загрузке адресов',
      };
    }
  },

  /**
   * Добавить новый адрес
   * @param {object} addressData - Данные адреса (street, building, apartment, etc.)
   * @returns {Promise<{success: boolean, address?: object}>}
   */
  async addAddress(addressData) {
    try {
      const address = await apiClient.post(ENDPOINTS.PROFILE.ADDRESSES, addressData);
      return { success: true, address };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при добавлении адреса',
        errors: error.data?.errors,
      };
    }
  },

  /**
   * Обновить адрес
   * @param {number|string} id - ID адреса
   * @param {object} addressData - Данные адреса
   * @returns {Promise<{success: boolean, address?: object}>}
   */
  async updateAddress(id, addressData) {
    try {
      const address = await apiClient.patch(ENDPOINTS.PROFILE.ADDRESS(id), addressData);
      return { success: true, address };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при обновлении адреса',
        errors: error.data?.errors,
      };
    }
  },

  /**
   * Удалить адрес
   * @param {number|string} id - ID адреса
   * @returns {Promise<{success: boolean}>}
   */
  async deleteAddress(id) {
    try {
      await apiClient.delete(ENDPOINTS.PROFILE.ADDRESS(id));
      return { success: true };
    } catch (error) {
      return {
        success: false,
        message: error.data?.message || error.message || 'Ошибка при удалении адреса',
      };
    }
  },
};
