/**
 * TypeScript type definitions for LearnR API
 * Based on backend Pydantic schemas
 */

// ==================== User & Auth ====================

export interface User {
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'learner' | 'admin' | 'super_admin';
  is_active: boolean;
  email_verified: boolean;
  two_factor_enabled: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ==================== Dashboard ====================

export interface DashboardData {
  user: User;
  overall_competency: number;
  questions_answered_today: number;
  questions_answered_week: number;
  study_streak_days: number;
  exam_readiness_percentage: number;
  days_until_exam: number | null;
  knowledge_areas: KnowledgeAreaProgress[];
  recent_sessions: RecentSession[];
  due_cards_count: number;
}

export interface KnowledgeAreaProgress {
  ka_id: string;
  ka_code: string;
  ka_name: string;
  weight_percentage: number;
  competency_score: number;
  total_questions_answered: number;
  correct_answers: number;
  accuracy_percentage: number;
}

export interface RecentSession {
  session_id: string;
  session_type: 'diagnostic' | 'practice' | 'mock_exam' | 'review';
  completed_at: string;
  score_percentage: number;
  total_questions: number;
  correct_answers: number;
}

// ==================== Practice Sessions ====================

export interface Session {
  session_id: string;
  session_type: string;
  started_at: string;
  completed_at: string | null;
  total_questions: number;
  correct_answers: number;
  score_percentage: number | null;
  is_completed: boolean;
}

export interface Question {
  question_id: string;
  question_text: string;
  question_type: 'multiple_choice' | 'true_false';
  answer_choices: AnswerChoice[];
  ka_id: string;
  ka_name: string;
  difficulty: number;
}

export interface AnswerChoice {
  choice_id: string;
  choice_text: string;
  choice_order: number;
}

export interface SubmitAnswerRequest {
  selected_choice_id: string;
  time_spent_seconds?: number;
  confidence_level?: number;
}

export interface AnswerFeedback {
  is_correct: boolean;
  correct_choice_id: string;
  explanation: string;
  competency_updated: boolean;
  new_competency_score?: number;
}

// ==================== Content Recommendations ====================

export interface ContentChunk {
  chunk_id: string;
  ka_id: string;
  ka_name?: string;
  content_title: string;
  content_text: string;
  content_type: string;
  source_document: string | null;
  source_page: string | null;
  source_section: string | null;
  difficulty_level: 'basic' | 'intermediate' | 'advanced' | null;
  expert_reviewed: boolean;
  helpfulness_score: number | null;
  efficacy_rate: number | null;
  created_at: string;
}

export interface ContentRecommendationResponse {
  strategy_used: string;
  total_recommendations: number;
  recommendations: ContentChunk[];
  context?: {
    weakest_knowledge_areas?: Array<{
      ka_id: string;
      ka_code: string;
      ka_name: string;
      competency_score: number;
    }>;
    explanation?: string;
  };
}

// ==================== Mock Exams ====================

export interface MockExamResponse {
  session_id: string;
  session_type: string;
  total_questions: number;
  exam_duration_minutes: number;
  started_at: string;
  instructions: string;
}

export interface KAPerformance {
  ka_id: string;
  ka_code: string | null;
  ka_name: string | null;
  weight_percentage: number;
  total_questions: number;
  correct_answers: number;
  score_percentage: number;
}

export interface MockExamResultsResponse {
  session_id: string;
  exam_type: string;
  completed_at: string | null;
  total_questions: number;
  correct_answers: number;
  incorrect_answers: number;
  score_percentage: number;
  passing_score: number;
  passed: boolean;
  margin: number;
  duration_seconds: number;
  duration_minutes: number;
  avg_seconds_per_question: number;
  performance_by_ka: KAPerformance[];
  strongest_areas: KAPerformance[];
  weakest_areas: KAPerformance[];
  next_steps: string[];
}

// ==================== Spaced Repetition ====================

export interface SpacedRepetitionCard {
  card_id: string;
  question_id: string;
  question_text: string;
  next_review_at: string;
  easiness_factor: number;
  interval_days: number;
  repetitions: number;
  is_due: boolean;
}

export interface DueCardsResponse {
  due_count: number;
  cards: SpacedRepetitionCard[];
}
