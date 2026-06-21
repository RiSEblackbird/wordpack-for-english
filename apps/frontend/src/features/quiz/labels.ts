import type {
  QuizDifficulty,
  QuizDomainIntensity,
  QuizFormatProfile,
  QuizGenerationDomain,
  QuizQuestionType,
} from './types';

export const FORMAT_PROFILE_LABELS: Record<QuizFormatProfile, string> = {
  single_passage: '1本長文',
  multi_document: '複数文書照合',
  dialogue_script: '会話・スクリプト',
  lecture_explanation: '講義・説明文',
  case_study: 'ケーススタディ',
  mixed: 'おまかせ混合',
};

export const GENERATION_DOMAIN_LABELS: Record<QuizGenerationDomain, string> = {
  technical: '技術的',
  academic: '学術的',
  business: 'ビジネス的',
  daily: '日常的',
};

export const DOMAIN_INTENSITY_LABELS: Record<QuizDomainIntensity, string> = {
  light: '軽め',
  standard: '標準',
  deep: '濃いめ',
};

export const DIFFICULTY_LABELS: Record<QuizDifficulty, string> = {
  easy: 'やさしい',
  medium: '標準',
  hard: '難しい',
};

export const QUESTION_TYPE_LABELS: Record<QuizQuestionType, string> = {
  main_idea: '主旨',
  detail: '詳細',
  inference: '推論',
  vocabulary: '語彙',
  reference: '指示語',
  sentence_insertion: '文挿入',
  purpose: '目的',
  cross_reference: '照合',
  next_action: '次の行動',
  organization: '構成',
};
