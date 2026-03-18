import React from "react";
import { useParams, useSearchParams } from "react-router-dom";

import { useSessionActions } from "../hooks/useSessionActions";
import { SessionDetailPage } from "../pages/SessionDetailPage";
import { useDraftSession } from "../hooks/useDraftSessions";

export function SessionRoute(): React.JSX.Element {
  const { sessionId } = useParams<{ sessionId?: string }>();
  const [searchParams] = useSearchParams();
  const sessionQuery = useDraftSession(sessionId ?? null);
  const initialReviewMode = searchParams.get("mode") === "edit" ? "edit" : "view";
  const actions = useSessionActions(sessionId ?? null, sessionQuery.data?.processSteps ?? []);

  return (
    <SessionDetailPage
      session={sessionQuery.data ?? null}
      selectedStepId={actions.selectedStepId}
      initialReviewMode={initialReviewMode}
      disabled={sessionQuery.isLoading || actions.disabled}
      exportingFormat={actions.exportingFormat}
      onBackToWorkspace={actions.backToWorkspace}
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
