import React from 'react';
import ReactDOM from 'react-dom/client';
import './i18n/i18n';
import { CacheProvider } from '@emotion/react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import { ErrorBoundary } from './components/ErrorBoundary';
import { NotificationProvider } from './hooks/useNotification';
import { cacheRtl, theme } from './theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 15000),
      staleTime: 10_000,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {/* Emotion RTL cache must wrap everything that uses MUI */}
    <CacheProvider value={cacheRtl}>
      <ThemeProvider theme={theme}>
        {/* Reset browser default styles */}
        <CssBaseline />
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <NotificationProvider>
              <ErrorBoundary>
                <App />
              </ErrorBoundary>
            </NotificationProvider>
          </AuthProvider>
          {/* React Query devtools — only visible in development */}
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
      </ThemeProvider>
    </CacheProvider>
  </React.StrictMode>
);
