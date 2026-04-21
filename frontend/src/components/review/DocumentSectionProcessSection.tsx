import React from "react";

import { labelForEnrichmentField } from "../../constants/enrichmentSectionLabels";
import { sessionService } from "../../services/sessionService";

type DocumentSectionProcessSectionProps = {
  sessionId: string;
  documentLabel: string;
  fieldIds: string[];
  /** Persisted + merged field bodies */
  fields: Record<string, string>;
  mode: "view" | "edit";
  disabled?: boolean;
  onAfterSave?: () => Promise<void> | void;
};

export function DocumentSectionProcessSection({
  sessionId,
  documentLabel,
  fieldIds,
  fields,
  mode,
  disabled,
  onAfterSave,
}: DocumentSectionProcessSectionProps): React.JSX.Element {
  const [selectedId, setSelectedId] = React.useState<string>(() => fieldIds[0] ?? "");
  const [draftText, setDraftText] = React.useState("");
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!fieldIds.length) {
      setSelectedId("");
      return;
    }
    if (!fieldIds.includes(selectedId)) {
      setSelectedId(fieldIds[0] ?? "");
    }
  }, [fieldIds, selectedId]);

  React.useEffect(() => {
    setDraftText(fields[selectedId] ?? "");
  }, [selectedId, fields]);

  async function handleSave(): Promise<void> {
    if (!selectedId || mode !== "edit") {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await sessionService.patchExportTextEnrichment(sessionId, { fields: { [selectedId]: draftText } });
      await onAfterSave?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  if (!fieldIds.length) {
    return (
      <section className="review-subsection panel stack" role="tabpanel">
        <div>
          <h3>Export sections</h3>
          <div className="artifact-meta">No template sections are registered for this document type.</div>
        </div>
        <div className="empty-state">Generate a draft first; enrichment runs after generation.</div>
      </section>
    );
  }

  const isReadOnly = mode === "view" || disabled;

  return (
    <section className="review-subsection panel stack" role="tabpanel" aria-label="Export sections">
      <div>
        <h3>Export sections</h3>
        <div className="artifact-meta">
          {documentLabel} — {fieldIds.length} section(s). Edits apply to Word/PDF export.
        </div>
      </div>

      {error ? (
        <div className="artifact-meta" style={{ color: "var(--color-danger, #c00)" }}>
          {error}
        </div>
      ) : null}

      <div className="review-layout">
        <div className="step-list review-step-list">
          {fieldIds.map((fieldId, index) => (
            <button
              key={fieldId}
              type="button"
              className={`button-secondary review-step-button review-step-button-document ${selectedId === fieldId ? "review-step-button-active" : ""}`}
              onClick={() => setSelectedId(fieldId)}
            >
              <span className="review-step-button-index">{index + 1}</span>
              <span className="review-step-button-label">{labelForEnrichmentField(fieldId)}</span>
            </button>
          ))}
        </div>

        <div className="review-detail-column stack">
          {selectedId ? (
            <>
              <div>
                <h4>{labelForEnrichmentField(selectedId)}</h4>
                <div className="artifact-meta">Field id: {selectedId}</div>
              </div>
              <textarea
                className="document-section-textarea"
                readOnly={isReadOnly}
                disabled={disabled}
                value={draftText}
                onChange={(event) => setDraftText(event.target.value)}
                rows={18}
                spellCheck
                aria-label={labelForEnrichmentField(selectedId)}
              />
              {mode === "edit" && !disabled ? (
                <div>
                  <button
                    type="button"
                    className="button-primary"
                    disabled={saving}
                    onClick={() => void handleSave()}
                  >
                    {saving ? "Saving…" : "Save section"}
                  </button>
                </div>
              ) : null}
            </>
          ) : null}
        </div>
      </div>
    </section>
  );
}
