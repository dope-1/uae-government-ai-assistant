"use client";

import { ChangeEvent, FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";

import { askAssistant } from "@/lib/api";
import { containsArabic, t } from "@/lib/i18n";
import { loadConversations, saveConversations } from "@/lib/storage";
import type {
  ChatMessage,
  Conversation,
  Feedback,
  Jurisdiction,
  Language,
} from "@/lib/types";
import { MessageCard } from "@/components/message-card";
import { ServiceExplorer } from "@/components/service-explorer";
import { SystemStatus } from "@/components/system-status";

const jurisdictions: Array<Jurisdiction | null> = [null, "Federal", "Abu Dhabi", "Dubai"];

function makeId(prefix: string): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return `${prefix}-${crypto.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function emptyConversation(language: Language, jurisdiction: Jurisdiction | null): Conversation {
  return {
    id: makeId("conversation"),
    title: language === "ar" ? "محادثة جديدة" : "New conversation",
    language,
    jurisdiction,
    messages: [],
    updatedAt: new Date().toISOString(),
  };
}

function titleFromQuestion(question: string): string {
  const cleaned = question.replace(/\s+/g, " ").trim();
  return cleaned.length > 48 ? `${cleaned.slice(0, 48)}…` : cleaned;
}

function jurisdictionLabel(value: Jurisdiction | null, language: Language): string {
  const labels = t(language);
  if (value === "Federal") return labels.federal;
  if (value === "Abu Dhabi") return labels.abuDhabi;
  if (value === "Dubai") return labels.dubai;
  return labels.autoJurisdiction;
}

const suggestions = {
  en: [
    { text: "How do I renew my driving licence in Dubai?", jurisdiction: "Dubai" as const },
    { text: "Which Abu Dhabi service handles driving licence renewal?", jurisdiction: "Abu Dhabi" as const },
    { text: "Where can I find official information about the UAE Golden Visa?", jurisdiction: "Federal" as const },
  ],
  ar: [
    { text: "كيف أجدد رخصة القيادة في دبي؟", jurisdiction: "Dubai" as const },
    { text: "ما الجهة المسؤولة عن تجديد رخصة القيادة في أبوظبي؟", jurisdiction: "Abu Dhabi" as const },
    { text: "أين أجد المعلومات الرسمية عن الإقامة الذهبية؟", jurisdiction: "Federal" as const },
  ],
};

export function GovernmentAssistant() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [language, setLanguage] = useState<Language>("en");
  const [jurisdiction, setJurisdiction] = useState<Jurisdiction | null>(null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeId) ?? null,
    [activeId, conversations],
  );
  const labels = t(language);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const stored = loadConversations();
      const initial = stored[0] ?? emptyConversation("en", null);
      const next = stored.length ? stored : [initial];
      setConversations(next);
      setActiveId(initial.id);
      setLanguage(initial.language);
      setJurisdiction(initial.jurisdiction);
      setHydrated(true);
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (hydrated) saveConversations(conversations);
  }, [conversations, hydrated]);

  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
  }, [language]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [activeConversation?.messages.length, sending]);

  function updateConversation(id: string, update: (conversation: Conversation) => Conversation) {
    setConversations((current) => {
      const target = current.find((conversation) => conversation.id === id);
      if (!target) return current;
      const updated = update(target);
      return [updated, ...current.filter((conversation) => conversation.id !== id)];
    });
  }

  function startNewConversation(nextLanguage = language, nextJurisdiction = jurisdiction): Conversation {
    const conversation = emptyConversation(nextLanguage, nextJurisdiction);
    setConversations((current) => [conversation, ...current]);
    setActiveId(conversation.id);
    setLanguage(nextLanguage);
    setJurisdiction(nextJurisdiction);
    setInput("");
    setSidebarOpen(false);
    window.setTimeout(() => textareaRef.current?.focus(), 0);
    return conversation;
  }

  function selectConversation(conversation: Conversation) {
    setActiveId(conversation.id);
    setLanguage(conversation.language);
    setJurisdiction(conversation.jurisdiction);
    setSidebarOpen(false);
  }

  function changeLanguage(nextLanguage: Language) {
    setLanguage(nextLanguage);
    if (activeId) {
      updateConversation(activeId, (conversation) => ({
        ...conversation,
        language: nextLanguage,
        updatedAt: new Date().toISOString(),
      }));
    }
  }

  function changeJurisdiction(nextJurisdiction: Jurisdiction | null) {
    setJurisdiction(nextJurisdiction);
    if (activeId) {
      updateConversation(activeId, (conversation) => ({
        ...conversation,
        jurisdiction: nextJurisdiction,
        updatedAt: new Date().toISOString(),
      }));
    }
  }

  function setFeedback(messageId: string, feedback: Feedback) {
    if (!activeId) return;
    updateConversation(activeId, (conversation) => ({
      ...conversation,
      messages: conversation.messages.map((message) =>
        message.id === messageId ? { ...message, feedback } : message,
      ),
      updatedAt: new Date().toISOString(),
    }));
  }

  async function submitMessage(rawText: string, forcedJurisdiction?: Jurisdiction) {
    const text = rawText.trim();
    if (!text || sending) return;

    const inferredLanguage: Language = containsArabic(text) ? "ar" : language;
    const targetJurisdiction = forcedJurisdiction ?? jurisdiction;
    let conversation = activeConversation;
    if (!conversation) conversation = startNewConversation(inferredLanguage, targetJurisdiction);
    const targetId = conversation.id;

    if (inferredLanguage !== language) setLanguage(inferredLanguage);
    if (forcedJurisdiction !== undefined) setJurisdiction(forcedJurisdiction);

    const userMessage: ChatMessage = {
      id: makeId("message"),
      role: "user",
      content: text,
      createdAt: new Date().toISOString(),
    };

    updateConversation(targetId, (current) => ({
      ...current,
      title: current.messages.length === 0 ? titleFromQuestion(text) : current.title,
      language: inferredLanguage,
      jurisdiction: targetJurisdiction,
      messages: [...current.messages, userMessage],
      updatedAt: new Date().toISOString(),
    }));
    setInput("");
    setSending(true);

    try {
      const response = await askAssistant(text, targetJurisdiction);
      const responseLanguage: Language = response.language.toLowerCase().startsWith("ar") ? "ar" : inferredLanguage;
      const assistantMessage: ChatMessage = {
        id: makeId("message"),
        role: "assistant",
        content: response.answer,
        createdAt: new Date().toISOString(),
        response,
        feedback: null,
      };
      setLanguage(responseLanguage);
      updateConversation(targetId, (current) => ({
        ...current,
        language: responseLanguage,
        jurisdiction: (response.jurisdiction as Jurisdiction | null) ?? current.jurisdiction,
        messages: [...current.messages, assistantMessage],
        updatedAt: new Date().toISOString(),
      }));
    } catch (caught) {
      const assistantMessage: ChatMessage = {
        id: makeId("message"),
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        error: caught instanceof Error ? caught.message : "The assistant could not complete this request.",
      };
      updateConversation(targetId, (current) => ({
        ...current,
        messages: [...current.messages, assistantMessage],
        updatedAt: new Date().toISOString(),
      }));
    } finally {
      setSending(false);
      window.setTimeout(() => textareaRef.current?.focus(), 0);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void submitMessage(input);
  }

  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submitMessage(input);
    }
  }

  function clearConversation() {
    if (!activeId) return;
    updateConversation(activeId, (conversation) => ({
      ...conversation,
      title: language === "ar" ? "محادثة جديدة" : "New conversation",
      messages: [],
      updatedAt: new Date().toISOString(),
    }));
  }

  const hasMessages = Boolean(activeConversation?.messages.length);

  return (
    <main className="app-shell" data-language={language}>
      <button
        className={`mobile-backdrop ${sidebarOpen ? "is-visible" : ""}`}
        type="button"
        aria-label={labels.closeMenu}
        onClick={() => setSidebarOpen(false)}
      />
      <aside className={`conversation-sidebar ${sidebarOpen ? "is-open" : ""}`} aria-label={labels.conversations}>
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true"><span>U</span><span>AE</span></div>
          <div>
            <strong>{labels.assistantName}</strong>
            <span>{labels.independent}</span>
          </div>
        </div>
        <button className="new-chat-button" type="button" onClick={() => startNewConversation()}>
          <span aria-hidden="true">＋</span> {labels.newChat}
        </button>
        <div className="history-heading">{labels.conversations}</div>
        <nav className="history-list">
          {conversations.length === 0 && <p>{labels.noHistory}</p>}
          {conversations.map((conversation) => (
            <button
              className={`history-item ${conversation.id === activeId ? "is-active" : ""}`}
              key={conversation.id}
              type="button"
              onClick={() => selectConversation(conversation)}
            >
              <span className="history-icon" aria-hidden="true">⌁</span>
              <span>
                <strong>{conversation.title}</strong>
                <small>{jurisdictionLabel(conversation.jurisdiction, language)}</small>
              </span>
            </button>
          ))}
        </nav>
        <div className="history-footnote">{labels.localHistory}</div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <button className="mobile-menu" type="button" onClick={() => setSidebarOpen(true)} aria-label={labels.menu}>☰</button>
          <div className="topbar-title">
            <span className="independent-badge">{labels.independent}</span>
            <strong>{jurisdictionLabel(jurisdiction, language)}</strong>
          </div>
          <div className="topbar-actions">
            <div className="language-toggle" role="group" aria-label="Language">
              <button className={language === "en" ? "is-active" : ""} type="button" onClick={() => changeLanguage("en")}>EN</button>
              <button className={language === "ar" ? "is-active" : ""} type="button" onClick={() => changeLanguage("ar")}>ع</button>
            </div>
            {hasMessages && (
              <button className="quiet-button" type="button" onClick={clearConversation}>{labels.clearConversation}</button>
            )}
          </div>
        </header>

        <div className="workspace-grid">
          <section className="chat-column">
            <div className="disclaimer-banner" role="note">
              <span aria-hidden="true">i</span>
              <p>{labels.disclaimer}</p>
            </div>

            <div className={`chat-stage ${hasMessages ? "has-messages" : ""}`}>
              {!hasMessages ? (
                <div className="empty-state">
                  <div className="empty-symbol" aria-hidden="true">⌘</div>
                  <span className="eyebrow">BILINGUAL · GROUNDED · CITED</span>
                  <h1>{labels.heroTitle}</h1>
                  <p>{labels.heroSubtitle}</p>
                  <div className="suggestion-label">{labels.suggested}</div>
                  <div className="suggestion-grid">
                    {suggestions[language].map((suggestion) => (
                      <button
                        key={suggestion.text}
                        type="button"
                        onClick={() => void submitMessage(suggestion.text, suggestion.jurisdiction)}
                        dir={language === "ar" ? "rtl" : "ltr"}
                      >
                        <span>{suggestion.text}</span><span aria-hidden="true">↗</span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="message-stream" aria-live="polite">
                  {activeConversation?.messages.map((message) => (
                    <MessageCard
                      key={message.id}
                      message={message}
                      language={language}
                      onFeedback={(feedback) => setFeedback(message.id, feedback)}
                    />
                  ))}
                  {sending && (
                    <div className="message-row is-assistant">
                      <div className="assistant-avatar" aria-hidden="true">AI</div>
                      <div className="thinking-card" aria-label="Assistant is retrieving official sources">
                        <span /><span /><span />
                        <em>{language === "ar" ? "جارٍ التحقق من المصادر المفهرسة…" : "Checking indexed official sources…"}</em>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            <div className="composer-wrap">
              <div className="jurisdiction-tabs" role="group" aria-label={labels.jurisdiction}>
                {jurisdictions.map((value) => (
                  <button
                    type="button"
                    key={value ?? "auto"}
                    className={jurisdiction === value ? "is-active" : ""}
                    onClick={() => changeJurisdiction(value)}
                  >
                    {jurisdictionLabel(value, language)}
                  </button>
                ))}
              </div>
              <form className="composer" onSubmit={onSubmit}>
                <textarea
                  ref={textareaRef}
                  rows={1}
                  value={input}
                  disabled={sending}
                  onChange={(event: ChangeEvent<HTMLTextAreaElement>) => setInput(event.target.value)}
                  onKeyDown={onComposerKeyDown}
                  placeholder={labels.placeholder}
                  aria-label={labels.placeholder}
                  dir={containsArabic(input) || language === "ar" ? "rtl" : "ltr"}
                />
                <button className="send-button" type="submit" disabled={sending || input.trim().length < 2}>
                  <span>{labels.send}</span>
                  <span aria-hidden="true">↑</span>
                </button>
              </form>
              <p className="composer-note">{labels.notProbability}</p>
            </div>
          </section>

          <aside className="context-column">
            <SystemStatus language={language} />
            <ServiceExplorer language={language} jurisdiction={jurisdiction} />
          </aside>
        </div>
      </section>
    </main>
  );
}
