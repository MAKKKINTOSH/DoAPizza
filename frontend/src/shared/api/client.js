import { API_URL } from '../config';

/**
 * Базовый HTTP клиент для работы с API
 */
class ApiClient {
  constructor(baseURL = API_URL) {
    this.baseURL = baseURL;
  }

  /**
   * Получить заголовки для запроса
   */
  getHeaders(customHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...customHeaders,
    };

    // Добавляем токен авторизации, если он есть
    const token = localStorage.getItem('doapizza_token');
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    return headers;
  }

  /**
   * Обработка ответа от сервера
   */
  async handleResponse(response) {
    const contentType = response.headers.get('content-type');
    const isJson = contentType && contentType.includes('application/json');

    let data;
    if (isJson) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const error = new Error(data?.message || data?.detail || `HTTP error! status: ${response.status}`);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  }

  /**
   * Базовый метод для выполнения запросов
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      ...options,
      headers: this.getHeaders(options.headers),
    };

    try {
      const response = await fetch(url, config);
      return await this.handleResponse(response);
    } catch (error) {
      // Обработка сетевых ошибок
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Ошибка сети. Проверьте подключение к интернету.');
      }
      throw error;
    }
  }

  /**
   * GET запрос
   */
  get(endpoint, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'GET',
    });
  }

  /**
   * POST запрос
   */
  post(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * PUT запрос
   */
  put(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /**
   * PATCH запрос
   */
  patch(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  /**
   * DELETE запрос
   */
  delete(endpoint, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'DELETE',
    });
  }

  /**
   * Загрузка файла (multipart/form-data)
   */
  upload(endpoint, formData, options = {}) {
    const headers = this.getHeaders();
    delete headers['Content-Type']; // Удаляем Content-Type для FormData

    return this.request(endpoint, {
      ...options,
      method: 'POST',
      headers,
      body: formData,
    });
  }
}

// Экспортируем единственный экземпляр клиента
export const apiClient = new ApiClient();
