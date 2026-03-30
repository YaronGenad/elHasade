import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from 'react';
import { User, Token } from '../types';
import { login as apiLogin, register as apiRegister, getMe } from '../api/auth';

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// SECURITY NOTE — JWT Storage Risk Assessment (Sprint 7)
// Current: localStorage. Vulnerable to XSS but not CSRF.
// Alternative: httpOnly cookies — immune to XSS but requires CSRF protection,
// backend Set-Cookie changes, and SameSite/Secure config.
// Mitigation: strict CSP in nginx.conf blocks inline scripts; Zod sanitization
// strips HTML from user inputs. Migration to httpOnly cookies is recommended
// for a future sprint if the threat model changes (e.g., third-party scripts).
const saveTokens = (tokens: Token) => {
  localStorage.setItem('access_token', tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
};

const clearStorage = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount, attempt to restore session from stored tokens
  useEffect(() => {
    const restoreSession = async () => {
      const accessToken = localStorage.getItem('access_token');
      if (!accessToken) {
        setIsLoading(false);
        return;
      }

      try {
        const me = await getMe();
        setUser(me);
      } catch {
        // Token may be expired; interceptor will attempt refresh.
        // If it ultimately fails the interceptor clears storage & redirects.
        clearStorage();
      } finally {
        setIsLoading(false);
      }
    };

    restoreSession();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await apiLogin(email, password);
    saveTokens(tokens);
    const me = await getMe();
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    clearStorage();
    setUser(null);
  }, []);

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      await apiRegister(email, password, fullName);
      // After registration, log the user in immediately
      const tokens = await apiLogin(email, password);
      saveTokens(tokens);
      const me = await getMe();
      setUser(me);
    },
    []
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        register,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
};
