import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Slider from '@mui/material/Slider';
import Alert from '@mui/material/Alert';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Grid from '@mui/material/Grid';
import Skeleton from '@mui/material/Skeleton';
import Tooltip from '@mui/material/Tooltip';
import SendIcon from '@mui/icons-material/Send';
import SearchIcon from '@mui/icons-material/Search';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { useTranslation } from 'react-i18next';
import { submitGeneration } from '../api/generations';
import { searchSimilar } from '../api/search';
import { getErrorMessage } from '../api/client';
import { StatusChip } from '../components/StatusChip';
import { useDebounce } from '../hooks/useDebounce';
import { AxiosError } from 'axios';

/** Strip HTML tags and trim whitespace to prevent XSS payloads reaching the API. */
const sanitize = (val: string) => val.replace(/<[^>]*>/g, '').trim();

const generationSchema = z.object({
  subject: z.string().min(1, 'שדה חובה / حقل مطلوب').max(200, 'ערך ארוך מדי / القيمة طويلة جداً').transform(sanitize),
  topic: z.string().min(1, 'שדה חובה / حقل مطلوب').max(200, 'ערך ארוך מדי / القيمة طويلة جداً').transform(sanitize),
  grade: z.string().min(1, 'שדה חובה / حقل مطلוب').max(50, 'ערך ארוך מדי / القيمة طويلة جداً').transform(sanitize),
  rounds: z.number().min(1).max(10),
});

type GenerationFormData = z.infer<typeof generationSchema>;

const formatSimilarityScore = (score: number) => `${Math.round(score * 100)}%`;

export const NewGenerationPage: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<GenerationFormData>({
    resolver: zodResolver(generationSchema),
    defaultValues: {
      rounds: 4,
    },
  });

  // Watch fields to build the search query
  const subject = watch('subject');
  const topic = watch('topic');
  const grade = watch('grade');

  // Build composite search query from form fields
  useEffect(() => {
    const parts = [subject, topic, grade].filter(Boolean);
    setSearchQuery(parts.join(' '));
  }, [subject, topic, grade]);

  const debouncedSearchQuery = useDebounce(searchQuery, 500);

  // Similarity search — only when we have meaningful input
  const { data: searchData, isFetching: isSearching } = useQuery({
    queryKey: ['search', debouncedSearchQuery],
    queryFn: () => searchSimilar(debouncedSearchQuery, 5, 1.0),
    enabled: debouncedSearchQuery.trim().length > 3,
    staleTime: 30_000,
  });

  const onSubmit = async (data: GenerationFormData) => {
    setErrorMessage(null);
    try {
      const response = await submitGeneration(data);
      navigate(`/generations/${response.generation_id}`);
    } catch (err) {
      setErrorMessage(getErrorMessage(err as AxiosError));
    }
  };

  const hasSimilarResults = (searchData?.count ?? 0) > 0;

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Page header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" fontWeight={700}>
          {t('generation.createTitle')}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
          {t('generation.createSubtitle')}
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Main form */}
        <Grid item xs={12} md={7}>
          <Card>
            <CardContent sx={{ p: { xs: 3, sm: 4 } }}>
              {errorMessage && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  {errorMessage}
                </Alert>
              )}

              <Box
                component="form"
                onSubmit={handleSubmit(onSubmit)}
                noValidate
                sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}
              >
                {/* Subject */}
                <TextField
                  {...register('subject')}
                  label={t('generation.subject')}
                  placeholder={t('generation.subjectPlaceholder')}
                  error={!!errors.subject}
                  helperText={errors.subject?.message}
                  autoFocus
                />

                {/* Topic */}
                <TextField
                  {...register('topic')}
                  label={t('generation.topic')}
                  placeholder={t('generation.topicPlaceholder')}
                  error={!!errors.topic}
                  helperText={errors.topic?.message}
                />

                {/* Grade */}
                <TextField
                  {...register('grade')}
                  label={t('generation.grade')}
                  placeholder={t('generation.gradePlaceholder')}
                  error={!!errors.grade}
                  helperText={errors.grade?.message}
                />

                {/* Rounds slider */}
                <Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Typography variant="body2" fontWeight={500}>
                      {t('generation.rounds')}
                    </Typography>
                    <Tooltip title={t('generation.roundsTooltip')}>
                      <InfoOutlinedIcon fontSize="small" color="action" sx={{ cursor: 'help' }} />
                    </Tooltip>
                  </Box>
                  <Box sx={{ px: 1 }}>
                    <Controller
                      name="rounds"
                      control={control}
                      render={({ field }) => (
                        <Slider
                          {...field}
                          min={1}
                          max={10}
                          step={1}
                          marks
                          valueLabelDisplay="on"
                          color="primary"
                          onChange={(_, value) => field.onChange(value)}
                        />
                      )}
                    />
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Typography variant="caption" color="text.secondary">1</Typography>
                    <Typography variant="caption" color="text.secondary">10</Typography>
                  </Box>
                </Box>

                {/* Submit button */}
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  disabled={isSubmitting}
                  endIcon={isSubmitting ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
                  sx={{ py: 1.5, mt: 1 }}
                >
                  {isSubmitting
                    ? t('generation.submitting')
                    : t('generation.submitButton')}
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Similarity suggestions sidebar */}
        <Grid item xs={12} md={5}>
          <Card sx={{ position: { md: 'sticky' }, top: { md: 80 } }}>
            <CardContent sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <SearchIcon color="primary" />
                <Typography variant="h6">
                  {t('generation.similarResults')}
                </Typography>
                {isSearching && <CircularProgress size={16} sx={{ ml: 1 }} />}
              </Box>

              {debouncedSearchQuery.trim().length <= 3 && (
                <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                  {t('generation.similarHint')}
                </Typography>
              )}

              {isSearching && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  {Array.from({ length: 3 }).map((_, i) => (
                    <Card key={i} variant="outlined">
                      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                        <Skeleton variant="text" width="60%" height={24} />
                        <Skeleton variant="text" width="80%" height={20} sx={{ mt: 0.5 }} />
                        <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                          <Skeleton variant="rectangular" width={60} height={24} sx={{ borderRadius: 4 }} />
                          <Skeleton variant="rectangular" width={80} height={24} sx={{ borderRadius: 4 }} />
                        </Box>
                      </CardContent>
                    </Card>
                  ))}
                </Box>
              )}

              {debouncedSearchQuery.trim().length > 3 && !isSearching && !hasSimilarResults && (
                <Alert severity="info" icon={false} sx={{ borderRadius: 2 }}>
                  {t('generation.noSimilar')}
                </Alert>
              )}

              {hasSimilarResults && (
                <>
                  <Alert severity="warning" sx={{ mb: 2, borderRadius: 2 }}>
                    {t('generation.foundSimilar', { count: searchData!.count })}
                  </Alert>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                    {searchData!.results.map((result) => (
                      <Card
                        key={result.generation_id}
                        variant="outlined"
                        sx={{
                          cursor: 'pointer',
                          transition: 'all 0.2s',
                          '&:hover': {
                            borderColor: 'primary.main',
                            boxShadow: '0 2px 8px rgba(0,121,107,0.2)',
                          },
                        }}
                        onClick={() => navigate(`/generations/${result.generation_id}`)}
                      >
                        <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                            <Typography variant="subtitle2" fontWeight={600} noWrap sx={{ maxWidth: '70%' }}>
                              {result.subject}
                            </Typography>
                            <Chip
                              label={formatSimilarityScore(result.similarity_score)}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                          </Box>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            {result.topic}
                          </Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mt: 1 }}>
                            <Box sx={{ display: 'flex', gap: 0.5 }}>
                              <Chip label={result.grade} size="small" variant="outlined" />
                              <Chip label={t('generation.roundsLabel', { rounds: result.rounds })} size="small" variant="outlined" />
                            </Box>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <StatusChip status={result.status} />
                              <OpenInNewIcon fontSize="small" color="action" />
                            </Box>
                          </Box>
                        </CardContent>
                      </Card>
                    ))}
                  </Box>
                </>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Container>
  );
};
