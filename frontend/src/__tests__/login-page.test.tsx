import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './helpers';
import { LoginPage } from '../pages/LoginPage';

// Mock AuthContext
const mockLogin = vi.fn();
const mockNavigate = vi.fn();

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    login: mockLogin,
    isAuthenticated: false,
    isLoading: false,
    user: null,
    logout: vi.fn(),
    register: vi.fn(),
  }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ state: null, pathname: '/login', search: '', hash: '', key: 'default' }),
  };
});

beforeEach(() => {
  vi.clearAllMocks();
});

describe('LoginPage', () => {
  it('renders the login form with email and password fields', () => {
    renderWithProviders(<LoginPage />);

    expect(screen.getByLabelText(/אימייל/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^סיסמה$/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /התחבר/ })).toBeInTheDocument();
  });

  it('renders the Al-Hasade branding', () => {
    renderWithProviders(<LoginPage />);
    expect(screen.getByText('Al-Hasade')).toBeInTheDocument();
  });

  it('shows link to register page', () => {
    renderWithProviders(<LoginPage />);
    expect(screen.getByText(/הרשמה/)).toBeInTheDocument();
  });

  it('shows validation error for empty email', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    await user.click(screen.getByRole('button', { name: /התחבר/ }));

    await waitFor(() => {
      expect(screen.getByText(/שדה חובה/)).toBeInTheDocument();
    });
  });

  it('shows validation error for invalid email', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText(/אימייל/), 'not-an-email');
    await user.type(screen.getByLabelText(/^סיסמה$/), 'password123');
    await user.click(screen.getByRole('button', { name: /התחבר/ }));

    await waitFor(() => {
      expect(screen.getByText(/אימייל לא תקינה/)).toBeInTheDocument();
    });
  });

  it('shows validation error for short password', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText(/אימייל/), 'test@example.com');
    await user.type(screen.getByLabelText(/^סיסמה$/), 'short');
    await user.click(screen.getByRole('button', { name: /התחבר/ }));

    await waitFor(() => {
      expect(screen.getByText(/לפחות 8 תווים/)).toBeInTheDocument();
    });
  });

  it('calls login and navigates on successful submit', async () => {
    mockLogin.mockResolvedValueOnce(undefined);
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText(/אימייל/), 'test@example.com');
    await user.type(screen.getByLabelText(/^סיסמה$/), 'password123');
    await user.click(screen.getByRole('button', { name: /התחבר/ }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123');
    });
  });

  it('shows error message on 401 login failure', async () => {
    const err = { response: { status: 401 }, isAxiosError: true };
    mockLogin.mockRejectedValueOnce(err);
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText(/אימייל/), 'test@example.com');
    await user.type(screen.getByLabelText(/^סיסמה$/), 'wrongpassword');
    await user.click(screen.getByRole('button', { name: /התחבר/ }));

    await waitFor(() => {
      expect(screen.getByText(/אימייל או סיסמה שגויים/)).toBeInTheDocument();
    });
  });

  it('toggles password visibility', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    const passwordField = screen.getByLabelText(/^סיסמה$/);
    expect(passwordField).toHaveAttribute('type', 'password');

    await user.click(screen.getByLabelText(/הצג\/הסתר סיסמה/));
    expect(passwordField).toHaveAttribute('type', 'text');

    await user.click(screen.getByLabelText(/הצג\/הסתר סיסמה/));
    expect(passwordField).toHaveAttribute('type', 'password');
  });
});
