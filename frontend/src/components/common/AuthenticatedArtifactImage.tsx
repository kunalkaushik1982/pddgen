import React, { useEffect, useState } from "react";

import { artifactService } from "../../services/artifactService";

type AuthenticatedArtifactImageProps = {
  artifactId: string;
  previewUrl?: string | null;
  alt: string;
  className?: string;
};

export function AuthenticatedArtifactImage({
  artifactId,
  previewUrl,
  alt,
  className,
}: AuthenticatedArtifactImageProps): React.JSX.Element {
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const imageUrl = previewUrl
    ? artifactService.resolveArtifactUrl(previewUrl)
    : artifactService.getArtifactContentUrl(artifactId);

  useEffect(() => {
    setLoadState("loading");
  }, [artifactId, previewUrl]);

  if (loadState === "error") {
    return <span className="muted">Image unavailable.</span>;
  }

  return (
    <>
      {loadState !== "ready" ? <span className="muted">Loading image...</span> : null}
      <img
        className={className}
        src={imageUrl}
        alt={alt}
        loading="lazy"
        style={loadState === "ready" ? undefined : { visibility: "hidden" }}
        onLoad={() => {
          setLoadState("ready");
        }}
        onError={() => {
          setLoadState("error");
        }}
      />
    </>
  );
}
