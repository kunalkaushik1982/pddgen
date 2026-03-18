import React, { useEffect, useState } from "react";

import { artifactService } from "../../services/artifactService";

type AuthenticatedArtifactImageProps = {
  artifactId: string;
  alt: string;
  className?: string;
};

export function AuthenticatedArtifactImage({
  artifactId,
  alt,
  className,
}: AuthenticatedArtifactImageProps): React.JSX.Element {
  const [objectUrl, setObjectUrl] = useState<string>("");
  const [error, setError] = useState(false);

  useEffect(() => {
    let isMounted = true;
    let nextObjectUrl = "";

    void artifactService
      .fetchArtifactBlob(artifactId)
      .then((blob) => {
        if (!isMounted) {
          return;
        }
        nextObjectUrl = window.URL.createObjectURL(blob);
        setObjectUrl(nextObjectUrl);
        setError(false);
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }
        setError(true);
      });

    return () => {
      isMounted = false;
      if (nextObjectUrl) {
        window.URL.revokeObjectURL(nextObjectUrl);
      }
    };
  }, [artifactId]);

  if (error) {
    return <span className="muted">Image unavailable.</span>;
  }

  if (!objectUrl) {
    return <span className="muted">Loading image…</span>;
  }

  return <img className={className} src={objectUrl} alt={alt} />;
}
