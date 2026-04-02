/**
 * Purpose: Placeholder frontend types for process steps and evidence.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\types\process.ts
 */

export type ConfidenceLevel = "high" | "medium" | "low" | "unknown";

export type EvidenceReference = {
  id: string;
  artifactId: string;
  kind: "video" | "transcript" | "screenshot" | "document";
  locator: string;
};

export type StepScreenshot = {
  id: string;
  artifactId: string;
  role: string;
  sequenceNumber: number;
  timestamp: string;
  selectionMethod: string;
  isPrimary: boolean;
  artifact: {
    id: string;
    name: string;
    kind: "screenshot";
    storagePath: string;
    previewUrl?: string | null;
    previewExpiresAt?: string | null;
  };
};

export type CandidateScreenshot = {
  id: string;
  artifactId: string;
  sequenceNumber: number;
  timestamp: string;
  sourceRole: string;
  selectionMethod: string;
  isSelected: boolean;
  artifact: {
    id: string;
    name: string;
    kind: "screenshot";
    storagePath: string;
    previewUrl?: string | null;
    previewExpiresAt?: string | null;
  };
};

export type ProcessStep = {
  id: string;
  processGroupId?: string | null;
  meetingId?: string | null;
  stepNumber: number;
  applicationName: string;
  actionText: string;
  sourceDataNote: string;
  timestamp: string;
  startTimestamp: string;
  endTimestamp: string;
  supportingTranscriptText: string;
  screenshotId: string;
  confidence: ConfidenceLevel;
  evidenceReferences: EvidenceReference[];
  screenshots: StepScreenshot[];
  candidateScreenshots: CandidateScreenshot[];
  editedByBa: boolean;
};

export type ProcessNote = {
  id: string;
  processGroupId?: string | null;
  meetingId?: string | null;
  text: string;
  relatedStepIds: string[];
  evidenceReferenceIds: string[];
  confidence: ConfidenceLevel;
  inferenceType: string;
};
