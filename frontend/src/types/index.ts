export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface SimilarQuery {
  generation_id: string;
  subject: string;
  topic: string;
  grade: string;
  rounds: number;
  similarity_score: number;
  created_at: string;
  status: string;
}

export interface GenerationResponse {
  generation_id: string;
  status: string;
  message: string;
  from_cache: boolean;
  similar_queries: SimilarQuery[];
}

export interface GenerationStatus {
  generation_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
  subject: string;
  topic: string;
  grade: string;
  rounds: number;
  result?: Record<string, unknown>;
  error?: string;
  material_id?: string;
}

// ── Materials / Approval (Sprint 4.5) ────────────────────────────────────────

export interface MaterialApprovalResponse {
  status: 'approved' | 'rejected';
  material_id: string;
  approval_count?: number;
}

export interface MaterialVersionItem {
  material_id: string;
  version: number;
  approval_count: number;
  times_served: number;
  subject: string;
  topic: string;
  grade: string;
  created_at?: string;
}

export interface MaterialVersionsResponse {
  subject: string;
  topic: string;
  grade: string;
  versions: MaterialVersionItem[];
}

export interface GenerationListItem {
  generation_id: string;
  status: string;
  created_at: string;
  completed_at?: string;
  subject: string;
  topic: string;
  grade: string;
  rounds: number;
}

export interface GenerationListResponse {
  generations: GenerationListItem[];
  limit: number;
  offset: number;
}

export interface SearchResult {
  generation_id: string;
  subject: string;
  topic: string;
  grade: string;
  rounds: number;
  similarity_score: number;
  created_at: string;
  status: string;
}

export interface SearchResponse {
  query: string;
  threshold: number;
  count: number;
  results: SearchResult[];
}

export interface SubmitGenerationData {
  subject: string;
  topic: string;
  grade: string;
  rounds: number;
  force_new?: boolean;
  include_stem?: boolean;
  stem_description?: string;
}

export type FileType =
  | 'student_pdf'
  | 'teacher_pdf'
  | `round${number}_comprehension`
  | `round${number}_methods`
  | `round${number}_precision`
  | `round${number}_vocabulary`
  | `round${number}_student_pdf`
  | `round${number}_teacher_pdf`
  | `round${number}_answer_key`
  | `round${number}_teacher_prep`;
