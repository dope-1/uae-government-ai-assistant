"use client";

import type { ReactNode } from "react";

import { containsArabic, t } from "@/lib/i18n";
import type { ChatMessage, Citation, Feedback, Language } from "@/lib/types";

function evidenceLabel(message: ChatMessage, language: Language): string {
  const response = message.response;
  if (!response || response.status === "unverified" || response.grounding.level === "insufficient") {
    return t(language).unverified;
  }
  if (response.grounding.level === "limited") return t(language).limited;
  return t(language).verified;
}

function evidenceClass(message: ChatMessage): string {
  const response = message.response;
  if (!response || response.status === "unverified" || response.grounding.level === "insufficient") {
    return "is-unverified";
  }
  if (response.grounding.level === "limited") return "is-limited";
  return "is-verified";
}

function renderAnswer(text: string, citations: Citation[]): ReactNode[] {
  const citationMap = new Map(citations.map((citation) => [citation.id, citation]));
  return text.split(/(\[S\d+\])/g).map((part, index) => {
    const marker = part.match(/^\[(S\d+)\]$/)?.[1];
    if (!marker || !citationMap.has(marker)) return <span key={`${index}-${part}`}>{part}</span>;
    return (
      <a
        className="citation-marker"
        href={`#citation-${citationMap.get(marker)?.chunk_id}`}
        key={`${index}-${marker}`}
        aria-label={`Jump to source ${marker}`}
      >
        {marker}
      </a>
    );
  });
}

function formatRetrieved(value: string | null, language: Language): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(language === "ar" ? "ar-AE" : "en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

interface CitationListProps {
  citations: Citation[];
  language: Language;
}

function CitationList({ citations, language }: CitationListProps) {
  const labels = t(language);
  if (citations.length === 0) return null;

  return (
    <div className="citation-list">
      <div className="citation-list-heading">
        <span>{labels.sources}</span>
        <span className="citation-count">{citations.length}</span>
      </div>
      {citations.map((citation) => (
        <details
          className="citation-card"
          id={`citation-${citation.chunk_id}`}
          key={citation.chunk_id}
        >
          <summary>
            <span className="citation-id">{citation.id}</span>
            <span className="citation-summary-copy">
              <strong>{citation.title}</strong>
              <span>
                {citation.authority} · {citation.jurisdiction}
              </span>
            </span>
            <span className="chevron" aria-hidden="true">⌄</span>
          </summary>
          <div className="citation-body">
            <p dir={containsArabic(citation.relevant_excerpt) ? "rtl" : "ltr"}>
              {citation.relevant_excerpt}
            </p>
            <div className="citation-meta">
              <span>
                {labels.retrieved}: {formatRetrieved(citation.retrieved_at, language)}
              </span>
              <a href={citation.url} target="_blank" rel="noreferrer noopener">
                {labels.openOfficial} ↗
              </a>
            </div>
          </div>
        </details>
      ))}
    </div>
  );
}

interface AssistantMessageProps {
  message: ChatMessage;
  language: Language;
  onFeedback: (feedback: Feedback) => void;
}

export function MessageCard({ message, language, onFeedback }: AssistantMessageProps) {
  const labels = t(language);
  const isUser = message.role === "user";
  const response = message.response;
  const messageDirection = containsArabic(message.content) ? "rtl" : "ltr";

  if (isUser) {
    return (
      <article className="message-row is-user">
        <div className="user-message" dir={messageDirection}>
          {message.content}
        </div>
      </article>
    );
  }

  return (
    <article className="message-row is-assistant">
      <div className="assistant-avatar" aria-hidden="true">AI</div>
      <div className="assistant-message">
        {message.error ? (
          <div className="assistant-error" role="alert">
            {message.error}
          </div>
        ) : (
          <>
            {response && (
              <div className="message-status-row">
                <span className={`evidence-pill ${evidenceClass(message)}`}>
                  <span className="status-dot" aria-hidden="true" />
                  {evidenceLabel(message, language)}
                </span>
                {response.jurisdiction && (
                  <span className="metadata-pill">{response.jurisdiction}</span>
                )}
                <span className="metadata-pill">{response.intent.replaceAll("_", " ")}</span>
              </div>
            )}
            <div className="answer-copy" dir={messageDirection}>
              {response ? renderAnswer(message.content, response.citations) : message.content}
            </div>
            {response && (
              <details className="grounding-details">
                <summary>{labels.evidence}</summary>
                <div className="grounding-grid">
                  <div>
                    <span>{labels.supportHeuristic}</span>
                    <strong>{response.grounding.support_score.toFixed(2)}</strong>
                  </div>
                  <div>
                    <span>{labels.jurisdiction}</span>
                    <strong>{response.jurisdiction ?? labels.autoJurisdiction}</strong>
                  </div>
                  <div>
                    <span>{labels.model}</span>
                    <strong>{response.model ?? "—"}</strong>
                  </div>
                </div>
                <p className="heuristic-note">{labels.notProbability}</p>
                {response.grounding.reasons.length > 0 && (
                  <ul className="grounding-reasons">
                    {response.grounding.reasons.map((reason) => <li key={reason}>{reason}</li>)}
                  </ul>
                )}
              </details>
            )}
            {response && <CitationList citations={response.citations} language={language} />}
            {!message.error && (
              <div className="feedback-row" title={labels.feedbackLocal}>
                <button
                  className={message.feedback === "up" ? "is-selected" : ""}
                  type="button"
                  onClick={() => onFeedback(message.feedback === "up" ? null : "up")}
                  aria-label={labels.useful}
                  aria-pressed={message.feedback === "up"}
                >
                  ↑
                </button>
                <button
                  className={message.feedback === "down" ? "is-selected" : ""}
                  type="button"
                  onClick={() => onFeedback(message.feedback === "down" ? null : "down")}
                  aria-label={labels.notUseful}
                  aria-pressed={message.feedback === "down"}
                >
                  ↓
                </button>
                <span>{labels.feedbackLocal}</span>
              </div>
            )}
          </>
        )}
      </div>
    </article>
  );
}
