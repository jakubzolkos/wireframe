
import { useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores";
import { apiClient, ApiError } from "@/lib/api-client";
import type { User, LoginRequest, RegisterRequest } from "@/types";
import { ROUTES } from "@/lib/constants";

export function useAuth() {
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading, setUser, setLoading, logout } = useAuthStore();

  // Check auth status on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const userData = await apiClient.get<User>("/auth/me");
        setUser(userData);
      } catch {
        setUser(null);
      }
    };

    if (isLoading) {
      checkAuth();
    }
  }, [isLoading, setUser]);

  const login = useCallback(
    async (credentials: LoginRequest) => {
      setLoading(true);
      try {
        // Backend expects OAuth2 form-data format
        const formData = new URLSearchParams();
        formData.append('username', credentials.email);
        formData.append('password', credentials.password);

        const response = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: formData,
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Login failed');
        }

        const tokens = await response.json();

        // Store tokens in localStorage for subsequent requests
        localStorage.setItem('access_token', tokens.access_token);
        localStorage.setItem('refresh_token', tokens.refresh_token);

        // Fetch user data
        const userData = await apiClient.get<User>("/auth/me");
        setUser(userData);

        navigate(ROUTES.DASHBOARD);
        return userData;
      } catch (error) {
        setLoading(false);
        throw error;
      }
    },
    [navigate, setUser, setLoading]
  );

  const register = useCallback(async (data: RegisterRequest) => {
    try {
      setLoading(true);
      const response = await apiClient.post<User>("/auth/register", data);
      setLoading(false);
      return response;
    } catch (error) {
      setLoading(false);
      throw error;
    }
  }, [setLoading]);

  const handleLogout = useCallback(async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        await apiClient.post("/auth/logout", { refresh_token: refreshToken });
      }
    } catch {
      // Ignore logout errors
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      logout();
      navigate(ROUTES.LOGIN);
    }
  }, [logout, navigate]);

  const refreshToken = useCallback(async () => {
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await apiClient.post<{ access_token: string; refresh_token: string }>(
        "/auth/refresh",
        { refresh_token: refreshToken }
      );

      // Store new tokens
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);

      // Re-fetch user after token refresh
      const userData = await apiClient.get<User>("/auth/me");
      setUser(userData);
      return true;
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        logout();
        navigate(ROUTES.LOGIN);
      }
      return false;
    }
  }, [logout, navigate, setUser]);

  return {
    user,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout: handleLogout,
    refreshToken,
  };
}
