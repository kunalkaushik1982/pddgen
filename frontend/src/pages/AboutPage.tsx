import React from "react";

import { releaseInfo } from "../config/releaseInfo";
import { uiCopy } from "../constants/uiCopy";
import type { AboutResponse } from "../services/aboutService";

type AboutPageProps = {
  about: AboutResponse;
};

export function AboutPage({ about }: AboutPageProps): React.JSX.Element {
  return (
    <section className="panel">
      <div className="section-heading">
        <h2>{uiCopy.aboutLabel}</h2>
        <p>Release, environment, and runtime component metadata for the current deployment.</p>
      </div>

      <div className="review-grid">
        <article className="panel">
          <h3 className="panel-title">Application</h3>
          <dl className="about-metadata">
            <div>
              <dt>Product</dt>
              <dd>{uiCopy.appTitle}</dd>
            </div>
            <div>
              <dt>Release</dt>
              <dd>{about.versions.release}</dd>
            </div>
            <div>
              <dt>Frontend</dt>
              <dd>{releaseInfo.frontend}</dd>
            </div>
            <div>
              <dt>Backend</dt>
              <dd>{about.versions.backend}</dd>
            </div>
            <div>
              <dt>Worker</dt>
              <dd>{about.versions.worker}</dd>
            </div>
          </dl>
        </article>

        <article className="panel">
          <h3 className="panel-title">Runtime</h3>
          <dl className="about-metadata">
            <div>
              <dt>API Name</dt>
              <dd>{about.app_name}</dd>
            </div>
            <div>
              <dt>Environment</dt>
              <dd>{about.environment}</dd>
            </div>
            <div>
              <dt>Auth Provider</dt>
              <dd>{about.auth_provider}</dd>
            </div>
            <div>
              <dt>AI Provider</dt>
              <dd>{about.ai_provider}</dd>
            </div>
          </dl>
        </article>
      </div>
    </section>
  );
}
