import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from 'react';
import Snackbar from '@mui/material/Snackbar';
import Alert, { AlertColor } from '@mui/material/Alert';

interface Notification {
  message: string;
  severity: AlertColor;
  key: number;
}

interface NotificationContextValue {
  notify: (message: string, severity?: AlertColor) => void;
  notifySuccess: (message: string) => void;
  notifyError: (message: string) => void;
  notifyWarning: (message: string) => void;
  notifyInfo: (message: string) => void;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

export const NotificationProvider = ({ children }: { children: ReactNode }) => {
  const [notification, setNotification] = useState<Notification | null>(null);

  const notify = useCallback((message: string, severity: AlertColor = 'info') => {
    setNotification({ message, severity, key: Date.now() });
  }, []);

  const notifySuccess = useCallback(
    (message: string) => notify(message, 'success'),
    [notify]
  );
  const notifyError = useCallback(
    (message: string) => notify(message, 'error'),
    [notify]
  );
  const notifyWarning = useCallback(
    (message: string) => notify(message, 'warning'),
    [notify]
  );
  const notifyInfo = useCallback(
    (message: string) => notify(message, 'info'),
    [notify]
  );

  const handleClose = (_?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') return;
    setNotification(null);
  };

  return (
    <NotificationContext.Provider
      value={{ notify, notifySuccess, notifyError, notifyWarning, notifyInfo }}
    >
      {children}
      <Snackbar
        open={!!notification}
        autoHideDuration={5000}
        onClose={handleClose}
        key={notification?.key}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {notification ? (
          <Alert
            severity={notification.severity}
            onClose={handleClose}
            variant="filled"
            sx={{ width: '100%', minWidth: 300 }}
          >
            {notification.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </NotificationContext.Provider>
  );
};

export const useNotification = (): NotificationContextValue => {
  const ctx = useContext(NotificationContext);
  if (!ctx) {
    throw new Error('useNotification must be used within NotificationProvider');
  }
  return ctx;
};
