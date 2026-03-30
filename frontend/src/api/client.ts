import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const BASE_URL = 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Map HTTP status codes and network errors to user-facing Hebrew/Arabic messages.
 */
export const getErrorMessage = (error: AxiosError): string => {
  if (!error.response) {
    // Network error — no response at all
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      return 'הבקשה ארכה יותר מדי זמן. אנא נסה שוב. / استغرق الطلب وقتاً طويلاً. يرجى المحاولة مرة أخرى.';
    }
    return 'אין חיבור לשרת. אנא בדוק את החיבור לאינטרנט. / لا يوجد اتصال بالخادم. يرجى التحقق من اتصال الإنترنت.';
  }

  const status = error.response.status;
  const serverDetail = (error.response.data as { detail?: string })?.detail;

  switch (status) {
    case 400:
      return serverDetail ?? 'הבקשה אינה תקינה / الطلب غير صالح';
    case 401:
      return 'יש להתחבר מחדש / يرجى تسجيل الدخول مرة أخرى';
    case 403:
      return 'אין הרשאה לביצוע פעולה זו / ليس لديك صلاحية لهذا الإجراء';
    case 404:
      return 'המשאב המבוקש לא נמצא / المورد المطلوب غير موجود';
    case 409:
      return serverDetail ?? 'התנגשות נתונים. אנא רענן ונסה שוב. / تعارض في البيانات. يرجى التحديث والمحاولة مرة أخرى.';
    case 422:
      return serverDetail ?? 'הנתונים שהוזנו אינם תקינים / البيانات المدخلة غير صالحة';
    case 429:
      return 'יותר מדי בקשות. אנא נסה שוב בעוד דקה. / طلبات كثيرة جداً. يرجى المحاولة بعد دقيقة.';
    case 500:
      return 'שגיאת שרת פנימית. הצוות קיבל התראה. / خطأ داخلي في الخادم. تم إخطار الفريق.';
    case 502:
    case 504:
      return 'השרת אינו זמין כרגע. אנא נסה שוב בעוד מספר דקות. / الخادم غير متاح حالياً. يرجى المحاولة بعد عدة دقائق.';
    case 503:
      return 'השרת בתחזוקה. אנא נסה שוב מאוחר יותר. / الخادم قيد الصيانة. يرجى المحاولة لاحقاً.';
    default:
      return serverDetail ?? 'אירעה שגיאה בלתי צפויה. אנא נסה שוב. / حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.';
  }
};

// Track if we're currently refreshing to avoid infinite loops
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: string) => void;
  reject: (reason: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else if (token) {
      resolve(token);
    }
  });
  failedQueue = [];
};

// Request interceptor — attach access token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const accessToken = localStorage.getItem('access_token');
    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — handle 401 and attempt token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('refresh_token');

      if (!refreshToken) {
        localStorage.clear();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      if (isRefreshing) {
        // Queue the request until refresh completes
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const response = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token: newRefreshToken } = response.data;
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', newRefreshToken);

        processQueue(null, access_token);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
