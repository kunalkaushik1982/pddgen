import React from "react";

import { ConfirmDialog } from "../components/common/ConfirmDialog";
import { useWorkspaceFlow } from "../hooks/useWorkspaceFlow";
import { UploadPage } from "../pages/UploadPage";
import { useAuth } from "../providers/AuthProvider";

export function WorkspaceRoute(): React.JSX.Element {
  const { user } = useAuth();
  const flow = useWorkspaceFlow();
  const showResumableDrafts = !(flow.uploadSessionId && flow.canGenerateDraft) && flow.resumableDraftSessions.length > 0;
  const [deleteDraftTarget, setDeleteDraftTarget] = React.useState<{ id: string; title: string } | null>(null);

  React.useEffect(() => {
    if (user?.username && flow.ownerId !== user.username) {
      flow.setOwnerId(user.username);
    }
  }, [flow.ownerId, flow.setOwnerId, user?.username]);

  return (
    <>
      {deleteDraftTarget ? (
        <ConfirmDialog
          title="Delete Draft?"
          description={`This will remove ${deleteDraftTarget.title} from Workspace and delete its uploaded files.`}
          confirmLabel="Delete Draft"
          tone="danger"
          busy={flow.deleteDraftPending}
          onCancel={() => setDeleteDraftTarget(null)}
          onConfirm={() => {
            void flow.deleteDraft(deleteDraftTarget.id).finally(() => setDeleteDraftTarget(null));
          }}
        />
      ) : null}

      <div className="session-controls-section">
        <section className="collapsible-section">
          <div className="collapsible-header">
            <div>
              <h2>1. Session Controls</h2>
              <p className="muted">Upload evidence, generate the PDD draft, and export the DOCX from one compact panel.</p>
            </div>
          </div>
          <UploadPage
            title={flow.title}
            ownerId={flow.ownerId}
            diagramType={flow.diagramType}
            uploads={flow.uploads}
            uploadItems={flow.uploadItems}
            uploadReady={flow.canGenerateDraft}
            disabled={flow.uploadPending || flow.generatePending}
            canUploadInputs={flow.canUploadInputs}
            canGenerateDraft={flow.canGenerateDraft}
            showHeader={false}
            ownerLocked
            showSubmitButton={false}
            actionBar={
              <div className="session-actions-row">
                <button
                  type="button"
                  className="button-secondary"
                  onClick={flow.uploadInputs}
                  disabled={!flow.canUploadInputs}
                >
                  {flow.isUploadingInputs ? "Uploading..." : "Upload Inputs"}
                </button>
                <button
                  type="button"
                  className="button-primary"
                  onClick={flow.generateDraft}
                  disabled={!flow.canGenerateDraft}
                >
                  Generate Draft
                </button>
              </div>
            }
            onTitleChange={flow.setTitle}
            onOwnerIdChange={flow.setOwnerId}
            onDiagramTypeChange={flow.setDiagramType}
            onFilesChange={flow.updateFiles}
            onRemoveSelectedFile={(field, index) => {
              if (field === "optionalArtifacts") {
                return;
              }
              void flow.removeSelectedFile(field, index);
            }}
            onSubmit={flow.generateDraft}
          />
        </section>
      </div>

      {showResumableDrafts ? (
        <section className="panel stack">
          <div className="section-header-inline">
            <div>
              <h2>Ready To Generate</h2>
              <p className="muted">These sessions already have uploaded inputs. Continue one to start generation without uploading again.</p>
            </div>
          </div>
          <div className="history-list">
            {flow.resumableDraftSessions.map((session) => (
              <div key={session.id} className="history-card">
                <div className="history-card-main">
                  <strong>{session.title}</strong>
                  <div className="artifact-meta">
                    {session.latestStageTitle} | updated {new Date(session.updatedAt).toLocaleString()}
                  </div>
                  <div className="artifact-meta">{session.latestStageDetail}</div>
                </div>
                <div className="button-row">
                  <button
                    type="button"
                    className="button-secondary"
                    disabled={flow.generatePending || flow.deleteDraftPending}
                    onClick={() => setDeleteDraftTarget({ id: session.id, title: session.title })}
                  >
                    Delete Draft
                  </button>
                  <button
                    type="button"
                    className="button-primary"
                    disabled={flow.generatePending || flow.deleteDraftPending}
                    onClick={() => void flow.resumeDraft(session.id)}
                  >
                    Continue Draft
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}
