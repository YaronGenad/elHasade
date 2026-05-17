import React, { useState } from 'react';
import { useNavigate, Link as RouterLink, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import InputAdornment from '@mui/material/InputAdornment';
import IconButton from '@mui/material/IconButton';
import Link from '@mui/material/Link';
import CircularProgress from '@mui/material/CircularProgress';
import EmailIcon from '@mui/icons-material/Email';
import LockIcon from '@mui/icons-material/Lock';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import { getErrorMessage } from '../api/client';
import { AxiosError } from 'axios';

const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'שדה חובה / حقل مطلوب')
    .email('כתובת אימייל לא תקינה / بريد إلكتروني غير صالح'),
  password: z
    .string()
    .min(8, 'הסיסמה חייבת להכיל לפחות 8 תווים / كلمة المرور يجب أن تحتوي على 8 أحرف على الأقل'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const LoginPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname ?? '/dashboard';

  // Redirect if already authenticated
  React.useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setErrorMessage(null);
    try {
      await login(data.email, data.password);
      navigate(from, { replace: true });
    } catch (err) {
      const axiosErr = err as AxiosError;
      if (axiosErr.response?.status === 401) {
        setErrorMessage(t('auth.invalidCredentials'));
      } else {
        setErrorMessage(getErrorMessage(axiosErr));
      }
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(150deg, #003d1a 0%, #1e6b3a 45%, #4c9a62 100%)',
        p: 2,
      }}
    >
      <Card sx={{ maxWidth: 440, width: '100%', boxShadow: '0 8px 40px rgba(0,0,0,0.25)' }}>
        <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
          {/* Header */}
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Box component="img"
              src="/logo.jpg"
              alt="אל השד״ה"
              sx={{ height: 80, width: 'auto', mb: 1.5, borderRadius: 2 }}
            />
            <Typography variant="h4" color="primary" gutterBottom fontWeight={800}>
              {t('common.appName')}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {t('common.appSubtitle')}
            </Typography>
          </Box>

          <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
            {t('auth.login')}
          </Typography>

          {errorMessage && (
            <Alert severity="error" role="alert" sx={{ mb: 2 }}>
              {errorMessage}
            </Alert>
          )}

          <Box
            component="form"
            onSubmit={handleSubmit(onSubmit)}
            noValidate
            sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}
          >
            <TextField
              {...register('email')}
              label={t('auth.email')}
              type="email"
              autoComplete="email"
              autoFocus
              error={!!errors.email}
              helperText={errors.email?.message}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <EmailIcon aria-hidden="true" color="action" />
                  </InputAdornment>
                ),
              }}
            />

            <TextField
              {...register('password')}
              label={t('auth.password')}
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              error={!!errors.password}
              helperText={errors.password?.message}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <LockIcon aria-hidden="true" color="action" />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowPassword((prev) => !prev)}
                      edge="end"
                      aria-label={t('auth.togglePasswordVisibility')}
                    >
                      {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={isSubmitting}
              sx={{ mt: 1, py: 1.5 }}
            >
              {isSubmitting ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                t('auth.loginButton')
              )}
            </Button>
          </Box>

          <Box sx={{ mt: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              {t('auth.noAccount')}{' '}
              <Link component={RouterLink} to="/register" color="primary" fontWeight={600}>
                {t('auth.register')}
              </Link>
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};
