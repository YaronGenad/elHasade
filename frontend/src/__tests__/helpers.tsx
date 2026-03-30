import React, { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, MemoryRouterProps } from 'react-router-dom';
import { theme } from '../theme';

/**
 * Creates a fresh QueryClient for each test to avoid shared state.
 */
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

interface WrapperOptions {
  routerProps?: MemoryRouterProps;
}

/**
 * Renders a component wrapped with all necessary providers (Theme, Router, QueryClient).
 */
export function renderWithProviders(
  ui: ReactElement,
  options?: RenderOptions & WrapperOptions
) {
  const { routerProps, ...renderOptions } = options ?? {};
  const queryClient = createTestQueryClient();

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <ThemeProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter {...routerProps}>{children}</MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );

  return render(ui, { wrapper: Wrapper, ...renderOptions });
}
