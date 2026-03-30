import { Component, ErrorInfo, ReactNode } from 'react';
import i18n from '../i18n/i18n';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import RefreshIcon from '@mui/icons-material/Refresh';
import HomeIcon from '@mui/icons-material/Home';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary]', error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/dashboard';
  };

  render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            bgcolor: 'background.default',
            p: 3,
          }}
        >
          <Card role="alert" sx={{ maxWidth: 520, width: '100%', textAlign: 'center' }}>
            <CardContent sx={{ p: { xs: 3, sm: 5 } }}>
              <ErrorOutlineIcon
                aria-hidden="true"
                sx={{ fontSize: 72, color: 'error.main', mb: 2 }}
              />
              <Typography variant="h5" fontWeight={700} gutterBottom>
                {i18n.t('errors.somethingWentWrong')}
              </Typography>
              <Typography
                variant="body1"
                color="text.secondary"
                sx={{ mb: 3 }}
              >
                {i18n.t('errors.unexpectedError')}
              </Typography>

              {this.state.error && (
                <Typography
                  variant="body2"
                  sx={{
                    bgcolor: 'grey.100',
                    p: 2,
                    borderRadius: 1,
                    fontFamily: 'monospace',
                    color: 'error.dark',
                    mb: 3,
                    direction: 'ltr',
                    textAlign: 'left',
                    maxHeight: 120,
                    overflow: 'auto',
                    fontSize: '0.8rem',
                  }}
                >
                  {this.state.error.message}
                </Typography>
              )}

              <Box
                sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}
              >
                <Button
                  variant="contained"
                  startIcon={<RefreshIcon aria-hidden="true" />}
                  onClick={this.handleReload}
                >
                  {i18n.t('errors.refreshPage')}
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<HomeIcon aria-hidden="true" />}
                  onClick={this.handleGoHome}
                >
                  {i18n.t('errors.goHome')}
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Box>
      );
    }

    return this.props.children;
  }
}
