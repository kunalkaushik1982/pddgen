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
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const imageUrl = artifactService.getArtifactContentUrl(artifactId);

  useEffect(() => {
    setLoadState("loading");
  }, [artifactId]);

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
