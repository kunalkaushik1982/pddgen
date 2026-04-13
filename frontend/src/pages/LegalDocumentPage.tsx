/**
 * Static legal documents (Terms, Privacy, Shipping, Contact, Refunds).
 */

import React from "react";
import { Link, useParams } from "react-router-dom";

import { LEGAL_DOCUMENTS, isLegalSlug, LEGAL_LAST_UPDATED } from "../constants/legalDocuments";
import { uiCopy } from "../constants/uiCopy";

export function LegalDocumentPage(): React.JSX.Element {
  const { slug } = useParams<{ slug: string }>();
  const resolved = slug && isLegalSlug(slug) ? LEGAL_DOCUMENTS[slug] : null;

  if (!resolved) {
    return (
      <main className="auth-shell legal-document-shell">
        <section className="panel auth-panel legal-document-panel">
          <p>Page not found.</p>
          <Link to="/auth" className="button-link">
            Back to sign in
          </Link>
        </section>
      </main>
    );
  }

  return (
    <main className="auth-shell legal-document-shell">
      <article className="panel auth-panel legal-document-panel">
        <p className="legal-document-back">
          <Link to="/auth" className="button-link">
            ← Back to sign in
          </Link>
        </p>
        <header className="legal-document-header">
          <p className="app-subtitle" style={{ margin: 0 }}>
            {uiCopy.appTitle}
          </p>
          <h1 className="legal-document-title">{resolved.title}</h1>
          <p className="muted legal-document-updated">Last updated: {LEGAL_LAST_UPDATED}</p>
        </header>
        <div className="legal-document-body stack">
          {resolved.sections.map((section, index) => (
            <section key={index} className="legal-document-section">
              {section.heading ? <h2 className="legal-document-h2">{section.heading}</h2> : null}
              {section.paragraphs.map((p, i) => (
                <p key={i} className="legal-document-p">
                  {p}
                </p>
              ))}
            </section>
          ))}
        </div>
      </article>
    </main>
  );
}
