/**
 * Authentication Hook
 *
 * Provides authentication functions and state
 */
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store/auth-store';
import apiClient, { handleApiError } from '@/lib/api-client';
import { LoginRequest, RegisterRequest, TokenResponse } from '@/types/api';

export function useAuth() {
  const router = useRouter();
  const { user, isAuthenticated, setAuth, logout: storeLogout, updateUser } = useAuthStore();

  const login = async (credentials: LoginRequest): Promise<{ success: boolean; error?: string }> => {
    try {
      const response = await apiClient.post<TokenResponse>('/auth/login', credentials);
      const { access_token, refresh_token } = response.data;

      // Get user data
      const userResponse = await apiClient.get('/auth/me', {
        headers: { Authorization: `Bearer ${access_token}` }
      });

      setAuth(userResponse.data, access_token, refresh_token);
      return { success: true };
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  };

  const register = async (data: RegisterRequest): Promise<{ success: boolean; error?: string }> => {
    try {
      // Register user
      await apiClient.post('/auth/register', data);

      // Auto-login after registration
      const loginResult = await login({
        email: data.email,
        password: data.password,
      });

      return loginResult;
    } catch (error) {
      return { success: false, error: handleApiError(error) };
    }
  };

  const logout = () => {
    storeLogout();
    router.push('/login');
  };

  const refreshUser = async () => {
    try {
      const response = await apiClient.get('/auth/me');
      updateUser(response.data);
    } catch (error) {
      console.error('Failed to refresh user:', error);
    }
  };

  return {
    user,
    isAuthenticated,
    login,
    register,
    logout,
    refreshUser,
  };
}
