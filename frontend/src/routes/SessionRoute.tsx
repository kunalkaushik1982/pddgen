import React from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { useSessionActions } from "../hooks/useSessionActions";
import { MeetingsPanel } from "../components/session/MeetingsPanel";
import { SessionDetailPage } from "../pages/SessionDetailPage";
import { useDraftSession } from "../hooks/useDraftSessions";

export function SessionRoute(): React.JSX.Element {
  const { sessionId } = useParams<{ sessionId?: string }>();
  const [searchParams] = useSearchParams();
  const sessionQuery = useDraftSession(sessionId ?? null);
  const initialReviewMode = searchParams.get("mode") === "edit" ? "edit" : "view";
  const latestActionLogTimestamp =
    sessionQuery.data?.actionLogs.length ? sessionQuery.data.actionLogs[sessionQuery.data.actionLogs.length - 1]?.createdAt ?? null : null;
  const latestActionLogTitle = sessionQuery.data?.actionLogs?.[0]?.title ?? null;
  const actions = useSessionActions(
    sessionId ?? null,
    sessionQuery.data?.processSteps ?? [],
    latestActionLogTimestamp,
    latestActionLogTitle,
  );

  return (
    <SessionDetailPage
      session={sessionQuery.data ?? null}
      meetingSection={
        sessionId ? (
          <MeetingsPanel
            sessionId={sessionId}
            session={sessionQuery.data ?? null}
            disabled={sessionQuery.isLoading || actions.disabled}
            onUpdateDraft={actions.generateDraft}
            updatingDraft={actions.generatingDraft}
          />
        ) : null
      }
      selectedStepId={actions.selectedStepId}
      initialReviewMode={initialReviewMode}
      disabled={sessionQuery.isLoading || actions.disabled}
      generatingScreenshots={actions.generatingScreenshots}
      exportingFormat={actions.exportingFormat}
      onGenerateScreenshots={actions.generateScreenshots}
      onExportDocx={actions.exportDocx}
      onExportPdf={actions.exportPdf}
      onSelectStep={actions.setSelectedStepId}
      onSaveStep={actions.saveStep}
      onSetPrimaryScreenshot={actions.setPrimaryScreenshot}
      onRemoveScreenshot={actions.removeScreenshot}
      onRefreshSession={actions.refreshSession}
      onSelectCandidateScreenshot={actions.selectCandidateScreenshot}
    />
  );
}
