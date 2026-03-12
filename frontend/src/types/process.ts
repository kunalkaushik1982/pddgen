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
  };
};

export type ProcessStep = {
  id: string;
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
  editedByBa: boolean;
};

export type ProcessNote = {
  id: string;
  text: string;
  relatedStepIds: string[];
  evidenceReferenceIds: string[];
  confidence: ConfidenceLevel;
  inferenceType: string;
};
