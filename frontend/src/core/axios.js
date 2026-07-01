/**
 * Axios instance: gắn access token, tự refresh khi 401, chuẩn hóa lỗi.
 */
import axios from 'axios';
import { AppError } from './errorHandler';

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:1111/api',
  timeout: 15000,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

const AUTH_KEYS = {
  TOKEN: 'auth_token',
  REFRESH_TOKEN: 'auth_refresh_token',
  USER: 'auth_user',
  IS_AUTHENTICATED: 'auth_is_authenticated',
};

const getToken = () => {
  try { return localStorage.getItem(AUTH_KEYS.TOKEN); } catch { return null; }
};
const getRefreshToken = () => {
  try { return localStorage.getItem(AUTH_KEYS.REFRESH_TOKEN); } catch { return null; }
};
const clearAuthData = () => {
  try { Object.values(AUTH_KEYS).forEach((k) => localStorage.removeItem(k)); } catch { /* noop */ }
};

let isLoggingOut = false;
let isRefreshing = false;
let refreshSubscribers = [];
const subscribe = (cb) => refreshSubscribers.push(cb);
const onRefreshed = (token) => {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
};

const refreshAccessToken = async () => {
  const refreshToken = getRefreshToken();
  if (!refreshToken) throw new AppError('Hết phiên đăng nhập', 401);

  const baseURL = axiosInstance.defaults.baseURL || '';
  const url = `${baseURL.replace(/\/$/, '')}/auth/refresh`;
  const { data } = await axios.post(url, { refreshToken }, { withCredentials: true });

  const accessToken = data?.data?.accessToken;
  if (!accessToken) throw new AppError('Không làm mới được token', 401);
  try { localStorage.setItem(AUTH_KEYS.TOKEN, accessToken); } catch { /* noop */ }
  return accessToken;
};

axiosInstance.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { response } = error;
    const originalRequest = error.config;

    if (!response) {
      if (error.code === 'ECONNABORTED') throw new AppError('Hết thời gian chờ. Kiểm tra kết nối.', 408);
      throw new AppError('Lỗi kết nối mạng. Kiểm tra lại đường truyền.', 0);
    }

    const { status, data } = response;

    if (status === 401) {
      const isAuthEndpoint = (originalRequest?.url || '').includes('/auth/');
      const canRefresh = Boolean(getRefreshToken()) && Boolean(getToken()) && !isAuthEndpoint;

      if (canRefresh && !originalRequest._retry) {
        originalRequest._retry = true;
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            subscribe((token) => {
              if (!token) return reject(new AppError('Hết phiên đăng nhập', 401));
              originalRequest.headers.Authorization = `Bearer ${token}`;
              resolve(axiosInstance(originalRequest));
            });
          });
        }
        isRefreshing = true;
        try {
          const token = await refreshAccessToken();
          isRefreshing = false;
          onRefreshed(token);
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return axiosInstance(originalRequest);
        } catch {
          isRefreshing = false;
          onRefreshed(null);
        }
      }

      if (!isLoggingOut && !isAuthEndpoint) {
        isLoggingOut = true;
        clearAuthData();
        window.dispatchEvent(new CustomEvent('auth:logout', { detail: { reason: 'unauthorized' } }));
        setTimeout(() => { isLoggingOut = false; }, 1000);
      }
    }

    throw new AppError(data?.message || 'Đã có lỗi xảy ra', status, data);
  },
);

export default axiosInstance;
