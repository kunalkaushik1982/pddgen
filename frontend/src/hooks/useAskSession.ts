import { useEffect, useState } from "react";

import { sessionService } from "../services/sessionService";
import type { ProcessNote, ProcessStep } from "../types/process";
import type { DraftSession, SessionAnswer, SessionAnswerCitation } from "../types/session";

type SessionChatEntry = {
  id: string;
  question: string;
  answer: SessionAnswer;
};

type EvidencePreview =
  | { kind: "step"; title: string; step: ProcessStep }
  | { kind: "note"; title: string; note: ProcessNote }
  | { kind: "transcript"; title: string; snippet: string };

export function useAskSession(session: DraftSession | null) {
  const [entries, setEntries] = useState<SessionChatEntry[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidencePreview | null>(null);

  useEffect(() => {
    setEntries([]);
    setErrorMessage(null);
    setSelectedEvidence(null);
  }, [session?.id]);

  async function ask(question: string): Promise<void> {
    if (!session) {
      return;
    }

    setErrorMessage(null);
    try {
      const answer = await sessionService.askSession(session.id, question);
      setEntries((current) => [
        {
          id: `${Date.now()}_${current.length}`,
          question,
          answer,
        },
        ...current,
      ]);
      if (answer.citations[0]) {
        selectCitation(answer.citations[0]);
      }
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Ask this Session could not answer that question.");
    }
  }

  function selectCitation(citation: SessionAnswerCitation): void {
    if (citation.sourceType === "step") {
      const stepNumberMatch = citation.id.match(/^step-(\d+)$/);
      const stepNumber = stepNumberMatch ? Number(stepNumberMatch[1]) : NaN;
      const matchingStep = session?.processSteps.find((step) => step.stepNumber === stepNumber);
      if (matchingStep) {
        setSelectedEvidence({
          kind: "step",
          title: `Step ${matchingStep.stepNumber}`,
          step: matchingStep,
        });
        return;
      }
    }

    if (citation.sourceType === "note") {
      const noteIndexMatch = citation.id.match(/^note-(\d+)$/);
      const noteIndex = noteIndexMatch ? Number(noteIndexMatch[1]) - 1 : -1;
      const matchingNote = noteIndex >= 0 ? session?.processNotes[noteIndex] : undefined;
      if (matchingNote) {
        setSelectedEvidence({
          kind: "note",
          title: citation.title,
          note: matchingNote,
        });
        return;
      }
    }

    setSelectedEvidence({
      kind: "transcript",
      title: citation.title,
      snippet: citation.snippet,
    });
  }

  return {
    entries,
    errorMessage,
    selectedEvidence,
    ask,
    selectCitation,
  };
}
