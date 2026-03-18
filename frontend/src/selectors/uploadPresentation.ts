import type { ArtifactUploadProgressItem } from "../types/workflow";

export function formatArtifactKind(kind: ArtifactUploadProgressItem["artifactKind"]): string {
  switch (kind) {
    case "video":
      return "Video";
    case "transcript":
      return "Transcript";
    case "template":
      return "Template";
    case "sop":
      return "SOP";
    case "diagram":
      return "Diagram";
    case "screenshot":
      return "Screenshot";
    default:
      return kind;
  }
}

export function getUploadStatusLabel(status: ArtifactUploadProgressItem["status"]): string {
  switch (status) {
    case "pending":
      return "Pending";
    case "uploading":
      return "Uploading";
    case "uploaded":
      return "Uploaded";
    case "failed":
      return "Failed";
    default:
      return status;
  }
}

export function formatFileSize(size: number): string {
  if (size >= 1024 * 1024 * 1024) {
    return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  }
  if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }
  if (size >= 1024) {
    return `${Math.round(size / 1024)} KB`;
  }
  return `${size} B`;
}
