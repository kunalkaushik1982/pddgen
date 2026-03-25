import React from "react";

type SessionSummaryPanelProps = {
  heading: string;
  subheading: string;
  summaryBullets: string[];
  sessionTitle: string;
  stepCount: number;
  diagramType: string;
  applicationsLabel: string;
  applicationCount: number;
  screenshotCount: number;
  primaryScreenshotCount: number;
  editedStepCount: number;
  noteCount: number;
};

export function SessionSummaryPanel({
  heading,
  subheading,
  summaryBullets,
  sessionTitle,
  stepCount,
  diagramType,
  applicationsLabel,
  applicationCount,
  screenshotCount,
  primaryScreenshotCount,
  editedStepCount,
  noteCount,
}: SessionSummaryPanelProps): React.JSX.Element {
  const [isExpanded, setIsExpanded] = React.useState(false);
  const visibleBullets = isExpanded ? summaryBullets : summaryBullets.slice(0, 12);
  const hasMoreBullets = summaryBullets.length > 12;

  return (
    <section className="review-subsection panel stack" role="tabpanel" aria-label="Summary">
      <div>
        <h3>Summary</h3>
        <div className="artifact-meta">Narrative summary for review before detailed process editing or export.</div>
      </div>

      <div className="summary-document">
        <div className="summary-document-label">Process summary</div>
        <div className="summary-document-card">
          <h4 className="summary-document-title">{heading}</h4>
          <div className="summary-document-subtitle">{subheading}</div>
          <ul className="summary-document-list">
            {visibleBullets.map((bullet, index) => (
              <li key={`${index}_${bullet}`}>{bullet}</li>
            ))}
          </ul>
          {hasMoreBullets ? (
            <button
              type="button"
              className="review-link-button"
              onClick={() => setIsExpanded((current) => !current)}
            >
              {isExpanded ? "See less" : `See more (${summaryBullets.length - visibleBullets.length} more)`}
            </button>
          ) : null}
        </div>
      </div>

      <div className="summary-meta-grid">
        <div className="summary-meta-card">
          <div className="artifact-meta">Session</div>
          <strong>{sessionTitle}</strong>
          <div className="summary-muted">{stepCount} steps | {diagramType}</div>
        </div>
        <div className="summary-meta-card">
          <div className="artifact-meta">Applications</div>
          <strong>{applicationsLabel}</strong>
          <div className="summary-muted">{applicationCount} application(s) involved</div>
        </div>
        <div className="summary-meta-card">
          <div className="artifact-meta">Evidence</div>
          <strong>{screenshotCount} screenshots</strong>
          <div className="summary-muted">{primaryScreenshotCount} primary selections</div>
        </div>
        <div className="summary-meta-card">
          <div className="artifact-meta">BA edits</div>
          <strong>{editedStepCount} edited steps</strong>
          <div className="summary-muted">{noteCount} notes captured</div>
        </div>
      </div>
    </section>
  );
}
