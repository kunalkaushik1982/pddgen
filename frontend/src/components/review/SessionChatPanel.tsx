/**
 * Purpose: Session-grounded Q&A panel for asking evidence-backed questions.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\components\review\SessionChatPanel.tsx
 */

import React, { useState } from "react";

import type { SessionAnswer } from "../../types/session";

type SessionChatEntry = {
  id: string;
  question: string;
  answer: SessionAnswer;
};

type SessionChatPanelProps = {
  disabled?: boolean;
  errorMessage?: string | null;
  entries: SessionChatEntry[];
  onAsk: (question: string) => Promise<void>;
};

export function SessionChatPanel({ disabled, errorMessage, entries, onAsk }: SessionChatPanelProps): JSX.Element {
  const [question, setQuestion] = useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextQuestion = question.trim();
    if (!nextQuestion) {
      return;
    }
    await onAsk(nextQuestion);
    setQuestion("");
  }

  return (
    <section className="review-subsection panel stack" role="tabpanel" aria-label="Ask this Session">
      <div>
        <h3>Ask this Session</h3>
        <div className="artifact-meta">Ask grounded questions using the uploaded transcript, extracted steps, and business notes.</div>
      </div>

      <form className="stack" onSubmit={handleSubmit}>
        <label className="field-group">
          <span>Question</span>
          <textarea
            rows={3}
            value={question}
            placeholder="Example: Which step mentions vendor validation in SAP?"
            onChange={(event) => setQuestion(event.target.value)}
            disabled={disabled}
          />
        </label>
        <div className="button-row">
          <button type="submit" className="button-primary" disabled={disabled || !question.trim()}>
            Ask this Session
          </button>
        </div>
      </form>

      {errorMessage ? <div className="empty-state">{errorMessage}</div> : null}

      {entries.length > 0 ? (
        <div className="session-chat-list">
          {entries.map((entry) => (
            <article key={entry.id} className="session-chat-card">
              <div className="session-chat-question">{entry.question}</div>
              <div className="session-chat-answer">{entry.answer.answer}</div>
              <div className={`session-chat-confidence session-chat-confidence-${entry.answer.confidence}`}>
                Confidence: {entry.answer.confidence}
              </div>
              {entry.answer.citations.length > 0 ? (
                <div className="session-chat-citations">
                  <strong>Citations</strong>
                  {entry.answer.citations.map((citation) => (
                    <div key={citation.id} className="session-chat-citation">
                      <div className="session-chat-citation-title">
                        {citation.title} <span className="artifact-meta">({citation.sourceType})</span>
                      </div>
                      <div className="artifact-meta">{citation.snippet}</div>
                    </div>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state">No questions asked yet. Start with a business, application, or step-level question.</div>
      )}
    </section>
  );
}
