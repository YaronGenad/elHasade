import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import React from 'react';
import { AuthProvider, useAuth } from '../contexts/AuthContext';

// Mock the API layer
vi.mock('../api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
  getMe: vi.fn(),
}));

import { login as apiLogin, register as apiRegister, getMe } from '../api/auth';

const mockLogin = vi.mocked(apiLogin);
const mockRegister = vi.mocked(apiRegister);
const mockGetMe = vi.mocked(getMe);

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe('useAuth', () => {
  it('throws when used outside AuthProvider', () => {
    expect(() => {
      renderHook(() => useAuth());
    }).toThrow('useAuth must be used within AuthProvider');
  });

  it('starts unauthenticated when no token in storage', async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
  });

  it('restores session from localStorage on mount', async () => {
    localStorage.setItem('access_token', 'stored-token');
    mockGetMe.mockResolvedValueOnce({
      id: '1',
      email: 'test@example.com',
      is_active: true,
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.email).toBe('test@example.com');
    expect(mockGetMe).toHaveBeenCalledOnce();
  });

  it('clears storage if session restore fails', async () => {
    localStorage.setItem('access_token', 'expired-token');
    mockGetMe.mockRejectedValueOnce(new Error('Unauthorized'));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(localStorage.getItem('access_token')).toBeNull();
  });

  it('login stores tokens and fetches user', async () => {
    mockLogin.mockResolvedValueOnce({
      access_token: 'new-access',
      refresh_token: 'new-refresh',
      token_type: 'bearer',
    });
    mockGetMe.mockResolvedValueOnce({
      id: '2',
      email: 'user@example.com',
      is_active: true,
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.login('user@example.com', 'password123');
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.email).toBe('user@example.com');
    expect(localStorage.getItem('access_token')).toBe('new-access');
    expect(localStorage.getItem('refresh_token')).toBe('new-refresh');
  });

  it('logout clears user and storage', async () => {
    localStorage.setItem('access_token', 'token');
    mockGetMe.mockResolvedValueOnce({
      id: '1',
      email: 'test@example.com',
      is_active: true,
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isAuthenticated).toBe(true);
    });

    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(localStorage.getItem('refresh_token')).toBeNull();
  });

  it('register calls register API then logs in', async () => {
    mockRegister.mockResolvedValueOnce({
      id: '3',
      email: 'new@example.com',
      is_active: true,
    });
    mockLogin.mockResolvedValueOnce({
      access_token: 'reg-access',
      refresh_token: 'reg-refresh',
      token_type: 'bearer',
    });
    mockGetMe.mockResolvedValueOnce({
      id: '3',
      email: 'new@example.com',
      full_name: 'New User',
      is_active: true,
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.register('new@example.com', 'password123', 'New User');
    });

    expect(mockRegister).toHaveBeenCalledWith('new@example.com', 'password123', 'New User');
    expect(mockLogin).toHaveBeenCalledWith('new@example.com', 'password123');
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.full_name).toBe('New User');
  });
});
