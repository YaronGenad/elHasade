import { createTheme } from '@mui/material/styles';
import createCache from '@emotion/cache';
import { prefixer } from 'stylis';
import rtlPlugin from 'stylis-plugin-rtl';

// RTL Emotion cache
export const cacheRtl = createCache({
  key: 'muirtl',
  stylisPlugins: [prefixer, rtlPlugin],
});

export const theme = createTheme({
  direction: 'rtl',
  palette: {
    primary: {
      main: '#1e6b3a',   // ירוק שדה עמוק — מהלוגו
      light: '#4c9a62',
      dark: '#003d1a',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#6a1b9a',   // סגול השיטה — מהרנדרינג
      light: '#9c4dcc',
      dark: '#4a235a',
      contrastText: '#ffffff',
    },
    background: {
      default: '#f2f7f3',  // גוון ירוק עדין
      paper: '#ffffff',
    },
    success: {
      main: '#388e3c',
    },
    error: {
      main: '#d32f2f',
    },
    info: {
      main: '#1976d2',
    },
    warning: {
      main: '#f57c00',
    },
  },
  typography: {
    fontFamily: [
      '"Noto Sans Hebrew"',
      '"Noto Sans Arabic"',
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      'Arial',
      'sans-serif',
    ].join(','),
    h4: {
      fontWeight: 700,
    },
    h5: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 10,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 8,
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: 'outlined',
        fullWidth: true,
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 12px rgba(0,0,0,0.08)',
          borderRadius: 12,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 600,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        },
      },
    },
  },
});
