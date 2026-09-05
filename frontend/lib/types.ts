export type Jurisdiction = "Federal" | "Abu Dhabi" | "Dubai";
export type Language = "en" | "ar";
export type Feedback = "up" | "down" | null;

export interface Citation {
  id: string;
  chunk_id: string;
  title: string;
  authority: string;
  url: string;
  jurisdiction: string;
  retrieved_at: string | null;
  relevant_excerpt: string;
  source_id: string;
  document_id: string;
}

export interface GroundingAssessment {
  level: "sufficient" | "limited" | "insufficient";
  support_score: number;
  focus_score: number;
  supporting_sources: number;
  focus_terms: string[];
  missing_focus_terms: string[];
  reasons: string[];
}

export interface RAGAnswer {
  answer: string;
  language: string;
  jurisdiction: string | null;
  intent: string;
  status: string;
  grounding: GroundingAssessment;
  citations: Citation[];
  model: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
}

export interface ServiceSummary {
  id: string;
  service_name: string;
  authority: string;
  jurisdiction: string;
  category: string | null;
  description: string | null;
  official_url: string;
}

export interface Readiness {
  status: string;
  dependencies: {
    postgres: boolean;
    redis: boolean;
  };
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  response?: RAGAnswer;
  error?: string;
  feedback?: Feedback;
}

export interface Conversation {
  id: string;
  title: string;
  language: Language;
  jurisdiction: Jurisdiction | null;
  messages: ChatMessage[];
  updatedAt: string;
}
