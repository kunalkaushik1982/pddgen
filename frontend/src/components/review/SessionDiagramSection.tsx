import React from "react";

type SessionDiagramSectionProps = {
  panelId: string;
  labelledBy: string;
  title: string;
  subtitle: string;
  children: React.ReactNode;
};

export function SessionDiagramSection({
  panelId,
  labelledBy,
  title,
  subtitle,
  children,
}: SessionDiagramSectionProps): React.JSX.Element {
  return (
    <section className="review-subsection panel stack" role="tabpanel" id={panelId} aria-labelledby={labelledBy}>
      <div>
        <h3>{title}</h3>
        <div className="artifact-meta">{subtitle}</div>
      </div>
      {children}
    </section>
  );
}
