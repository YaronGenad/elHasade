import React from 'react';
import { useTranslation } from 'react-i18next';
import Chip, { ChipProps } from '@mui/material/Chip';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';

interface StatusChipProps {
  status: string;
  size?: ChipProps['size'];
}

const statusConfig: Record<
  string,
  { label: string; color: ChipProps['color']; icon: React.ReactElement }
> = {
  pending: {
    label: 'ממתין / قيد الانتظار',
    color: 'default',
    icon: <HourglassEmptyIcon fontSize="small" />,
  },
  processing: {
    label: 'מעבד / جارٍ المعالجة',
    color: 'info',
    icon: <AutorenewIcon fontSize="small" />,
  },
  completed: {
    label: 'הושלם / مكتمل',
    color: 'success',
    icon: <CheckCircleIcon fontSize="small" />,
  },
  failed: {
    label: 'נכשל / فشل',
    color: 'error',
    icon: <ErrorIcon fontSize="small" />,
  },
};

export const StatusChip: React.FC<StatusChipProps> = ({ status, size = 'small' }) => {
  const { t } = useTranslation();
  const config = statusConfig[status] ?? {
    label: status,
    color: 'default' as ChipProps['color'],
    icon: <HourglassEmptyIcon fontSize="small" />,
  };
  const label = status in statusConfig ? t(`status.${status}`) : status;

  return (
    <Chip
      label={label}
      color={config.color}
      size={size}
      icon={config.icon}
      variant="filled"
    />
  );
};
