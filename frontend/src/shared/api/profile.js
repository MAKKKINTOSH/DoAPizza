import { authApi } from './auth';

/**
 * Профиль — использует auth API (GET /api/auth/users/{id}/)
 */
export const profileApi = {
  getProfile(userId) {
    return authApi.getUser(userId);
  },
};
