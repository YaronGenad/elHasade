import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Pagination from '@mui/material/Pagination';
import Skeleton from '@mui/material/Skeleton';
import AddCircleIcon from '@mui/icons-material/AddCircle';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DownloadIcon from '@mui/icons-material/Download';
import InboxIcon from '@mui/icons-material/Inbox';
import { getGenerations, downloadFile } from '../api/generations';
import { getErrorMessage } from '../api/client';
import { StatusChip } from '../components/StatusChip';
import { useNotification } from '../hooks/useNotification';
import { GenerationListItem } from '../types';
import { AxiosError } from 'axios';
import { useTranslation } from 'react-i18next';

const PAGE_SIZE = 10;

const formatDate = (iso: string) => {
  try {
    return new Intl.DateTimeFormat('he-IL', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
};

const hasActiveItems = (items: GenerationListItem[]) =>
  items.some((g) => g.status === 'pending' || g.status === 'processing');

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { notifyError } = useNotification();
  const [page, setPage] = useState(1);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const offset = (page - 1) * PAGE_SIZE;

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['generations', page],
    queryFn: () => getGenerations(PAGE_SIZE, offset),
    // Poll every 10 seconds if there are pending/processing items
    refetchInterval: (query) => {
      const generations = query.state.data?.generations ?? [];
      return hasActiveItems(generations) ? 10_000 : false;
    },
    staleTime: 5_000,
  });

  const handleView = (id: string) => {
    navigate(`/generations/${id}`);
  };

  const handleQuickDownload = async (id: string) => {
    setDownloadingId(id);
    try {
      await downloadFile(id, 'student_pdf');
    } catch (err) {
      notifyError(getErrorMessage(err as AxiosError));
    } finally {
      setDownloadingId(null);
    }
  };

  const totalPages = data
    ? Math.ceil((data.generations.length === PAGE_SIZE ? offset + PAGE_SIZE + 1 : offset + data.generations.length) / PAGE_SIZE)
    : 1;

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Page header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 4,
          flexWrap: 'wrap',
          gap: 2,
        }}
      >
        <Box>
          <Typography variant="h4" component="h1" fontWeight={700}>
            {t('dashboard.title')}
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
            {t('dashboard.subtitle')}
          </Typography>
        </Box>
        <Button
          variant="contained"
          size="large"
          startIcon={<AddCircleIcon />}
          onClick={() => navigate('/generate')}
        >
          {t('dashboard.newGeneration')}
        </Button>
      </Box>

      {/* Error state */}
      {isError && (
        <Alert severity="error" sx={{ mb: 3 }} role="alert">
          {error && 'response' in (error as object)
            ? getErrorMessage(error as AxiosError)
            : t('dashboard.loadError')}
        </Alert>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <Card>
          <CardContent>
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} variant="rectangular" height={52} sx={{ mb: 1, borderRadius: 1 }} />
            ))}
          </CardContent>
        </Card>
      )}

      {/* Empty state */}
      {!isLoading && data && data.generations.filter((g) => g.status !== 'failed').length === 0 && (
        <Card>
          <CardContent
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              py: 8,
              gap: 2,
            }}
          >
            <InboxIcon sx={{ fontSize: 72, color: 'text.disabled' }} aria-hidden="true" />
            <Typography variant="h6" color="text.secondary">
              {t('dashboard.emptyTitle')}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t('dashboard.emptySubtitle')}
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddCircleIcon />}
              onClick={() => navigate('/generate')}
              sx={{ mt: 1 }}
            >
              {t('dashboard.newGeneration')}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Generations table */}
      {!isLoading && data && data.generations.filter((g) => g.status !== 'failed').length > 0 && (
        <>
          <TableContainer component={Paper} sx={{ borderRadius: 2 }}>
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: 'primary.main' }}>
                  {[t('dashboard.tableSubject'), t('dashboard.tableTopic'), t('dashboard.tableGrade'), t('dashboard.tableRounds'), t('dashboard.tableStatus'), t('dashboard.tableDate'), t('dashboard.tableActions')].map(
                    (header) => (
                      <TableCell
                        key={header}
                        sx={{ color: 'white', fontWeight: 700 }}
                      >
                        {header}
                      </TableCell>
                    )
                  )}
                </TableRow>
              </TableHead>
              <TableBody>
                {data.generations.filter((gen) => gen.status !== 'failed').map((gen) => (
                  <TableRow
                    key={gen.generation_id}
                    hover
                    sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                  >
                    <TableCell sx={{ fontWeight: 500 }}>{gen.subject}</TableCell>
                    <TableCell>{gen.topic}</TableCell>
                    <TableCell>{gen.grade}</TableCell>
                    <TableCell align="center">{gen.rounds}</TableCell>
                    <TableCell>
                      <StatusChip status={gen.status} />
                    </TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap', fontSize: '0.85rem', color: 'text.secondary' }}>
                      {formatDate(gen.created_at)}
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Tooltip title={t('dashboard.viewDetails')}>
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleView(gen.generation_id)}
                            aria-label={t('dashboard.viewDetails')}
                          >
                            <VisibilityIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        {gen.status === 'completed' && (
                          <Tooltip title={t('dashboard.downloadStudentPdf')}>
                            <IconButton
                              size="small"
                              color="secondary"
                              onClick={() => handleQuickDownload(gen.generation_id)}
                              disabled={downloadingId === gen.generation_id}
                              aria-label={t('dashboard.downloadStudentPdf')}
                            >
                              {downloadingId === gen.generation_id ? (
                                <CircularProgress size={16} />
                              ) : (
                                <DownloadIcon fontSize="small" />
                              )}
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Pagination */}
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
            <Pagination
              count={totalPages}
              page={page}
              onChange={(_, value) => setPage(value)}
              color="primary"
              shape="rounded"
              aria-label={t('dashboard.title')}
            />
          </Box>
        </>
      )}
    </Container>
  );
};
