import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CardHeader from '@mui/material/CardHeader';
import Grid from '@mui/material/Grid';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import LinearProgress from '@mui/material/LinearProgress';
import Divider from '@mui/material/Divider';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import Skeleton from '@mui/material/Skeleton';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import DownloadIcon from '@mui/icons-material/Download';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import SchoolIcon from '@mui/icons-material/School';
import ClassIcon from '@mui/icons-material/Class';
import RepeatIcon from '@mui/icons-material/Repeat';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import RefreshIcon from '@mui/icons-material/Refresh';
import { useTranslation } from 'react-i18next';
import { getGeneration, downloadFile, submitGeneration } from '../api/generations';
import { approveMaterial, rejectMaterial, getMaterialVersions } from '../api/materials';
import { StatusChip } from '../components/StatusChip';
import { useNotification } from '../hooks/useNotification';
import { getErrorMessage } from '../api/client';
import { MaterialVersionItem } from '../types';
import { AxiosError } from 'axios';

// ── Roadmap summary display ───────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const RoadmapSummary: React.FC<{ result: Record<string, any> }> = ({ result }) => {
  const roadmap = result?.roadmap ?? {};
  const rounds: Array<Record<string, unknown>> = roadmap?.rounds ?? [];
  const goals = roadmap?.learning_goals ?? {};
  const steamConnections: string[] = roadmap?.steam_connections ?? [];

  const GoalList: React.FC<{ items: string[] }> = ({ items }) => (
    <Box component="ul" sx={{ m: 0, pl: 2.5, '& li': { mb: 0.5 } }}>
      {items.map((item: string, i: number) => (
        <Typography key={i} component="li" variant="body2">{item}</Typography>
      ))}
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Unit title + text type */}
      {roadmap.unit_title && (
        <Box>
          <Typography variant="h5" fontWeight={700} gutterBottom>
            {roadmap.unit_title}
          </Typography>
          {roadmap.central_text_type && (
            <Typography variant="body1" color="text.secondary">
              סוג טקסט: {roadmap.central_text_type}
            </Typography>
          )}
        </Box>
      )}

      {/* STEAM connections */}
      {steamConnections.length > 0 && (
        <Box>
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>חיבורי STEAM</Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {steamConnections.map((s: string, i: number) => (
              <Chip key={i} label={s} size="small" color="primary" variant="outlined" />
            ))}
          </Box>
        </Box>
      )}

      {/* Learning goals */}
      {(goals.knowledge?.length || goals.skills?.length || goals.values?.length) ? (
        <Box>
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>מטרות לימוד</Typography>
          <Grid container spacing={2}>
            {goals.knowledge?.length > 0 && (
              <Grid item xs={12} sm={4}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>ידע</Typography>
                <GoalList items={goals.knowledge} />
              </Grid>
            )}
            {goals.skills?.length > 0 && (
              <Grid item xs={12} sm={4}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>מיומנויות</Typography>
                <GoalList items={goals.skills} />
              </Grid>
            )}
            {goals.values?.length > 0 && (
              <Grid item xs={12} sm={4}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>ערכים</Typography>
                <GoalList items={goals.values} />
              </Grid>
            )}
          </Grid>
        </Box>
      ) : null}

      {/* Per-round breakdown */}
      {rounds.length > 0 && (
        <Box>
          <Typography variant="subtitle2" fontWeight={600} gutterBottom>פירוט סבבים</Typography>
          {rounds.map((rnd: Record<string, unknown>, idx: number) => {
            const comp = rnd.comprehension as Record<string, string> | undefined;
            const methods = rnd.methods as Record<string, string> | undefined;
            const precision = rnd.precision as Record<string, string> | undefined;
            const vocab = rnd.vocabulary as Record<string, string> | undefined;
            return (
              <Accordion key={idx} disableGutters elevation={0}
                sx={{ border: '1px solid', borderColor: 'divider', mb: 1, borderRadius: '8px !important', '&:before': { display: 'none' } }}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Chip label={`${rnd.round ?? idx + 1}`} size="small" color="primary" sx={{ minWidth: 32 }} />
                    <Typography fontWeight={500}>סבב {rnd.round ?? idx + 1}</Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={2}>
                    {comp && (
                      <Grid item xs={12} sm={6}>
                        <Typography variant="caption" color="primary" fontWeight={700}>הבנת הנקרא — {comp.text_type}</Typography>
                        <Typography variant="body2" sx={{ mt: 0.5 }}>{comp.description}</Typography>
                        {comp.discussion_focus && (
                          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                            דיון: {comp.discussion_focus}
                          </Typography>
                        )}
                      </Grid>
                    )}
                    {methods && (
                      <Grid item xs={12} sm={6}>
                        <Typography variant="caption" color="primary" fontWeight={700}>שיטות — {methods.writing_type}</Typography>
                        <Typography variant="body2" sx={{ mt: 0.5 }}>{methods.description}</Typography>
                      </Grid>
                    )}
                    {precision && (
                      <Grid item xs={12} sm={6}>
                        <Typography variant="caption" color="primary" fontWeight={700}>דיוק — {precision.activity_type}</Typography>
                        <Typography variant="body2" sx={{ mt: 0.5 }}>{precision.description}</Typography>
                      </Grid>
                    )}
                    {vocab && (
                      <Grid item xs={12} sm={6}>
                        <Typography variant="caption" color="primary" fontWeight={700}>אוצר מילים</Typography>
                        <Typography variant="body2" sx={{ mt: 0.5 }}>{(vocab as Record<string, string>).description}</Typography>
                      </Grid>
                    )}
                  </Grid>
                </AccordionDetails>
              </Accordion>
            );
          })}
        </Box>
      )}
    </Box>
  );
};

// File type definitions per round
interface FileDefinition {
  key: string;
  label: string;
  labelAr: string;
}

const GLOBAL_FILES: FileDefinition[] = [
  { key: 'student_pdf', label: 'PDF תלמיד', labelAr: 'PDF الطالب' },
  { key: 'teacher_pdf', label: 'PDF מורה', labelAr: 'PDF المعلم' },
];

const ROUND_FILES: FileDefinition[] = [
  { key: 'comprehension', label: 'הבנת הנקרא', labelAr: 'فهم القراءة' },
  { key: 'methods', label: 'שיטות', labelAr: 'أساليب' },
  { key: 'precision', label: 'דיוק', labelAr: 'دقة' },
  { key: 'vocabulary', label: 'אוצר מילים', labelAr: 'المفردات' },
  { key: 'student_pdf', label: 'PDF תלמיד', labelAr: 'PDF الطالب' },
  { key: 'teacher_pdf', label: 'PDF מורה', labelAr: 'PDF المعلم' },
  { key: 'answer_key', label: 'מפתח תשובות', labelAr: 'مفتاح الإجابات' },
  { key: 'teacher_prep', label: 'הכנת מורה', labelAr: 'تحضير المعلم' },
];

const formatDate = (iso?: string) => {
  if (!iso) return '—';
  try {
    return new Intl.DateTimeFormat('he-IL', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(new Date(iso));
  } catch {
    return iso;
  }
};

interface DownloadButtonProps {
  generationId: string;
  fileType: string;
  label: string;
}

const DownloadButton: React.FC<DownloadButtonProps> = ({ generationId, fileType, label }) => {
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState(false);

  const handleDownload = async () => {
    setIsDownloading(true);
    setError(false);
    try {
      await downloadFile(generationId, fileType);
    } catch {
      setError(true);
      setTimeout(() => setError(false), 3000);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <Button
      variant={error ? 'outlined' : 'outlined'}
      color={error ? 'error' : 'primary'}
      size="small"
      onClick={handleDownload}
      disabled={isDownloading}
      aria-label={label}
      startIcon={
        isDownloading ? <CircularProgress size={14} /> : <DownloadIcon fontSize="small" />
      }
      sx={{ minWidth: 140 }}
    >
      {label}
    </Button>
  );
};

export const GenerationDetailPage: React.FC = () => {
  const { t, i18n } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { notifySuccess, notifyError } = useNotification();
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [progressInfo, setProgressInfo] = useState<{ pct: number; stage: string }>({ pct: 0, stage: '' });
  const viewStartRef = React.useRef<number | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['generation', id],
    queryFn: () => getGeneration(id!),
    enabled: !!id,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(2000 * 2 ** attemptIndex, 20000),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'pending' || status === 'processing') {
        // Backoff: start at 5s, grow if the query has been failing
        const errorCount = query.state.fetchFailureCount;
        return Math.min(5000 * (1 + errorCount), 30000);
      }
      return false;
    },
    staleTime: 2_000,
  });

  // Fetch versions when material data is available
  const { data: versionsData } = useQuery({
    queryKey: ['materialVersions', data?.subject, data?.topic, data?.grade],
    queryFn: () =>
      getMaterialVersions(data!.subject, data!.topic, data!.grade),
    enabled: !!(data?.status === 'completed' && data.subject && data.topic && data.grade),
    staleTime: 10_000,
  });

  const versions: MaterialVersionItem[] = versionsData?.versions ?? [];
  const effectiveMaterialId = selectedVersionId ?? data?.material_id ?? null;

  const isActive = data?.status === 'pending' || data?.status === 'processing';

  // Progress estimation — counts from when the user first opens this page,
  // not from created_at (which could be hours old for stuck/resumed generations).
  useEffect(() => {
    if (!isActive) {
      viewStartRef.current = null;
      return;
    }

    // Record the moment we first see an active generation
    if (viewStartRef.current === null) {
      viewStartRef.current = Date.now();
    }

    const rounds = data?.rounds ?? 1;
    // Measured: ~120s per round on Gemini Flash. Add 20s overhead for roadmap + save.
    const totalEstimated = 20 + rounds * 120;

    // Stage thresholds as fraction of totalEstimated.
    // Stations build (stage2) is the long part → 15% to 85%.
    const STAGES = [
      { threshold: 0,    label: t('detail.progressStage0') },  // 0–5%:  waiting
      { threshold: 0.05, label: t('detail.progressStage1') },  // 5–15%: roadmap
      { threshold: 0.15, label: t('detail.progressStage2') },  // 15–85%: stations (bulk)
      { threshold: 0.85, label: t('detail.progressStage3') },  // 85–95%: PDF
      { threshold: 0.95, label: t('detail.progressStage4') },  // 95–99%: saving
    ];

    const compute = () => {
      const elapsed = (Date.now() - viewStartRef.current!) / 1000;
      const fraction = Math.min(0.99, Math.max(0, elapsed / totalEstimated));
      const pct = Math.round(fraction * 100);
      const stage = [...STAGES].reverse().find(s => fraction >= s.threshold)?.label ?? STAGES[0].label;
      setProgressInfo({ pct, stage });
    };

    compute();
    const interval = setInterval(compute, 1000);
    return () => clearInterval(interval);
  }, [isActive, data?.rounds, t]);

  const handleApprove = async () => {
    if (!effectiveMaterialId) return;
    setApprovalLoading(true);
    try {
      await approveMaterial(effectiveMaterialId);
      notifySuccess(t('detail.approved'));
      queryClient.invalidateQueries({ queryKey: ['materialVersions'] });
    } catch (err) {
      notifyError(getErrorMessage(err as AxiosError));
    } finally {
      setApprovalLoading(false);
    }
  };

  const handleReject = async () => {
    if (!effectiveMaterialId) return;
    setApprovalLoading(true);
    try {
      await rejectMaterial(effectiveMaterialId);
      // Use cache if other versions exist; only generate fresh when cache is exhausted
      const hasOtherVersions = versions.some(v => v.material_id !== effectiveMaterialId);
      const res = await submitGeneration({
        subject: data!.subject,
        topic: data!.topic,
        grade: data!.grade,
        rounds: data!.rounds,
        force_new: !hasOtherVersions,
      });
      navigate(`/generations/${res.generation_id}`);
    } catch (err) {
      notifyError(getErrorMessage(err as AxiosError));
      setApprovalLoading(false);
    }
  };

  if (!id) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error" role="alert">{t('detail.invalidId')}</Alert>
      </Container>
    );
  }

  if (isError) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }} role="alert">
          {t('dashboard.loadError')}
        </Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/dashboard')}>
          {t('common.backToDashboard')}
        </Button>
      </Container>
    );
  }

  const isCompleted = data?.status === 'completed';
  const isFailed = data?.status === 'failed';

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Back button */}
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate('/dashboard')}
        sx={{ mb: 3 }}
        color="inherit"
      >
        {t('common.backToDashboard')}
      </Button>

      {/* Header card */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
          {isLoading ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Skeleton variant="text" width="60%" height={40} />
              <Skeleton variant="text" width="40%" />
              <Skeleton variant="rectangular" width={120} height={32} sx={{ borderRadius: 4 }} />
            </Box>
          ) : (
            <>
              <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 2, mb: 3 }}>
                <Box>
                  <Typography variant="h4" fontWeight={700} gutterBottom>
                    {data?.subject}
                  </Typography>
                  <Typography variant="h6" color="text.secondary">
                    {data?.topic}
                  </Typography>
                </Box>
                <StatusChip status={data?.status ?? 'pending'} size="medium" />
              </Box>

              {/* Metadata grid */}
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ClassIcon color="primary" fontSize="small" />
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        {t('detail.grade')}
                      </Typography>
                      <Typography variant="body2" fontWeight={500}>
                        {data?.grade}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <RepeatIcon color="primary" fontSize="small" />
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        {t('detail.rounds')}
                      </Typography>
                      <Typography variant="body2" fontWeight={500}>
                        {data?.rounds}
                      </Typography>
                    </Box>
                  </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      {t('detail.createdAt')}
                    </Typography>
                    <Typography variant="body2" fontWeight={500}>
                      {formatDate(data?.created_at)}
                    </Typography>
                  </Box>
                </Grid>
                {data?.completed_at && (
                  <Grid item xs={6} sm={3}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">
                        {t('detail.completedAt')}
                      </Typography>
                      <Typography variant="body2" fontWeight={500}>
                        {formatDate(data.completed_at)}
                      </Typography>
                    </Box>
                  </Grid>
                )}
              </Grid>
            </>
          )}
        </CardContent>
      </Card>

      {/* Processing / pending state */}
      {isActive && (
        <Card sx={{ mb: 3 }}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
              <CircularProgress size={32} />
              <Box sx={{ flex: 1 }}>
                <Typography variant="h6">
                  {progressInfo.stage || (data?.status === 'pending' ? t('detail.pending') : t('detail.processing'))}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t('detail.autoRefresh')}
                </Typography>
              </Box>
              <Typography variant="h6" fontWeight={700} color="primary" sx={{ minWidth: 48, textAlign: 'right' }}>
                {progressInfo.pct}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={progressInfo.pct}
              color="primary"
              sx={{ borderRadius: 2, height: 8 }}
              aria-busy={true}
              aria-valuenow={progressInfo.pct}
            />
          </CardContent>
        </Card>
      )}

      {/* Failed state */}
      {isFailed && (
        <Card sx={{ mb: 3, borderColor: 'error.main', borderWidth: 1, borderStyle: 'solid' }}>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              <ErrorOutlineIcon color="error" fontSize="large" />
              <Typography variant="h6" color="error">
                {t('detail.failed')}
              </Typography>
            </Box>
            {data?.error && (
              <Typography
                variant="body2"
                sx={{
                  bgcolor: 'error.lighter',
                  p: 2,
                  borderRadius: 1,
                  fontFamily: 'monospace',
                  color: 'error.dark',
                  mt: 1,
                }}
              >
                {data.error}
              </Typography>
            )}
            <Button
              variant="contained"
              onClick={() => navigate('/generate')}
              sx={{ mt: 2 }}
            >
              {t('detail.retry')}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Completed — downloads */}
      {isCompleted && data && (
        <>
          {/* Approval action bar */}
          <Card sx={{ mb: 3, border: '2px solid', borderColor: 'primary.light' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                {t('detail.reviewTitle')}
              </Typography>

              {/* Version selector (shown when multiple versions exist) */}
              {versions.length > 1 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {t('detail.versionsTitle')}
                  </Typography>
                  <ToggleButtonGroup
                    value={effectiveMaterialId}
                    exclusive
                    onChange={(_, val) => val && setSelectedVersionId(val)}
                    size="small"
                  >
                    {versions.map((v) => (
                      <ToggleButton key={v.material_id} value={v.material_id}>
                        {t('detail.version', { version: v.version, count: v.approval_count })}
                      </ToggleButton>
                    ))}
                  </ToggleButtonGroup>
                </Box>
              )}

              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mt: 1 }}>
                <Button
                  variant="contained"
                  color="success"
                  startIcon={
                    approvalLoading ? <CircularProgress size={16} color="inherit" /> : <CheckCircleOutlineIcon />
                  }
                  disabled={approvalLoading || !effectiveMaterialId}
                  onClick={handleApprove}
                >
                  {t('detail.approve')}
                </Button>

                <Button
                  variant="outlined"
                  color="warning"
                  startIcon={
                    approvalLoading ? <CircularProgress size={16} color="inherit" /> : <RefreshIcon />
                  }
                  disabled={approvalLoading || !effectiveMaterialId}
                  onClick={handleReject}
                >
                  {t('detail.reject')}
                </Button>

              </Box>
            </CardContent>
          </Card>

          {/* Global downloads */}
          <Card sx={{ mb: 3 }}>
            <CardHeader
              avatar={<MenuBookIcon color="primary" />}
              title={
                <Typography variant="h6" fontWeight={600}>
                  {t('detail.globalDownloads')}
                </Typography>
              }
            />
            <Divider />
            <CardContent>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                {GLOBAL_FILES.map((file) => {
                  const fileLabel = i18n.language === 'ar' ? file.labelAr : file.label;
                  return (
                    <DownloadButton
                      key={file.key}
                      generationId={data.generation_id}
                      fileType={file.key}
                      label={fileLabel}
                    />
                  );
                })}
              </Box>
            </CardContent>
          </Card>

          {/* Per-round downloads */}
          <Card>
            <CardHeader
              avatar={<SchoolIcon color="primary" />}
              title={
                <Typography variant="h6" fontWeight={600}>
                  {t('detail.roundDownloads')}
                </Typography>
              }
            />
            <Divider />
            <CardContent sx={{ pt: 2 }}>
              {Array.from({ length: data.rounds }, (_, i) => i + 1).map((round) => (
                <Accordion key={round} disableGutters elevation={0} sx={{ border: '1px solid', borderColor: 'divider', mb: 1, borderRadius: '8px !important', '&:before': { display: 'none' } }}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Chip
                        label={`${round}`}
                        size="small"
                        color="primary"
                        sx={{ minWidth: 32 }}
                      />
                      <Typography fontWeight={500}>
                        {t('detail.round', { num: round })}
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5 }}>
                      {ROUND_FILES.map((file) => {
                        const fileLabel = i18n.language === 'ar' ? file.labelAr : file.label;
                        return (
                          <DownloadButton
                            key={file.key}
                            generationId={data.generation_id}
                            fileType={`round${round}_${file.key}`}
                            label={fileLabel}
                          />
                        );
                      })}
                    </Box>
                  </AccordionDetails>
                </Accordion>
              ))}
            </CardContent>
          </Card>

          {/* Result summary (if structured data available) */}
          {data.result && Object.keys(data.result).length > 0 && (
            <Card sx={{ mt: 3 }}>
              <CardHeader
                title={
                  <Typography variant="h6" fontWeight={600}>
                    {t('detail.resultSummary')}
                  </Typography>
                }
              />
              <Divider />
              <CardContent sx={{ p: 3 }}>
                <RoadmapSummary result={data.result as Record<string, unknown>} />
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Loading placeholders for downloads section */}
      {isLoading && (
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Skeleton variant="text" width="30%" height={32} sx={{ mb: 2 }} />
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} variant="rectangular" width={150} height={36} sx={{ borderRadius: 1 }} />
              ))}
            </Box>
          </CardContent>
        </Card>
      )}

    </Container>
  );
};
