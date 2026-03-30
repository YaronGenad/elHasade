import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from './helpers';
import { NewGenerationPage } from '../pages/NewGenerationPage';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../api/generations', () => ({
  submitGeneration: vi.fn(),
}));

vi.mock('../api/search', () => ({
  searchSimilar: vi.fn().mockResolvedValue({ query: '', threshold: 1, count: 0, results: [] }),
}));

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: '1', email: 'test@example.com', is_active: true },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
  }),
}));

import { submitGeneration } from '../api/generations';
const mockSubmit = vi.mocked(submitGeneration);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('NewGenerationPage', () => {
  it('renders the form with all required fields', () => {
    renderWithProviders(<NewGenerationPage />);

    expect(screen.getByLabelText(/^נושא$/)).toBeInTheDocument();
    expect(screen.getByLabelText(/נושא משנה/)).toBeInTheDocument();
    expect(screen.getByLabelText(/כיתה/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /צור חומרי לימוד/ })).toBeInTheDocument();
  });

  it('renders similarity search sidebar', () => {
    renderWithProviders(<NewGenerationPage />);
    const matches = screen.getAllByText(/תוצאות דומות/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it('shows validation errors for empty required fields', async () => {
    const user = userEvent.setup();
    renderWithProviders(<NewGenerationPage />);

    await user.click(screen.getByRole('button', { name: /צור חומרי לימוד/ }));

    await waitFor(() => {
      const errors = screen.getAllByText(/שדה חובה/);
      expect(errors.length).toBeGreaterThanOrEqual(3);
    });
  });

  it('submits the form and navigates on success', async () => {
    mockSubmit.mockResolvedValueOnce({
      generation_id: 'gen-123',
      status: 'pending',
      message: 'Created',
      from_cache: false,
      similar_queries: [],
    });

    const user = userEvent.setup();
    renderWithProviders(<NewGenerationPage />);

    await user.type(screen.getByLabelText(/^נושא$/), 'מתמטיקה');
    await user.type(screen.getByLabelText(/נושא משנה/), 'שברים');
    await user.type(screen.getByLabelText(/כיתה/), 'כיתה ה');
    await user.click(screen.getByRole('button', { name: /צור חומרי לימוד/ }));

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          subject: 'מתמטיקה',
          topic: 'שברים',
          grade: 'כיתה ה',
          rounds: 4,
          force_new: false,
        })
      );
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/generations/gen-123');
    });
  });

  it('shows error message on submission failure', async () => {
    mockSubmit.mockRejectedValueOnce({
      response: { status: 500, data: {} },
      isAxiosError: true,
    });

    const user = userEvent.setup();
    renderWithProviders(<NewGenerationPage />);

    await user.type(screen.getByLabelText(/^נושא$/), 'מתמטיקה');
    await user.type(screen.getByLabelText(/נושא משנה/), 'שברים');
    await user.type(screen.getByLabelText(/כיתה/), 'כיתה ה');
    await user.click(screen.getByRole('button', { name: /צור חומרי לימוד/ }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  it('sanitizes HTML from form inputs (XSS prevention)', async () => {
    mockSubmit.mockResolvedValueOnce({
      generation_id: 'gen-456',
      status: 'pending',
      message: 'Created',
      from_cache: false,
      similar_queries: [],
    });

    const user = userEvent.setup();
    renderWithProviders(<NewGenerationPage />);

    await user.type(screen.getByLabelText(/^נושא$/), '<script>alert("xss")</script>math');
    await user.type(screen.getByLabelText(/נושא משנה/), 'topic<img onerror=alert(1)>');
    await user.type(screen.getByLabelText(/כיתה/), 'grade');
    await user.click(screen.getByRole('button', { name: /צור חומרי לימוד/ }));

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          subject: expect.not.stringContaining('<script>'),
          topic: expect.not.stringContaining('<img'),
        })
      );
    });
  });
});
