/**
 * Purpose: Placeholder frontend types for draft sessions and outputs.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\types\session.ts
 */

import type { ProcessNote, ProcessStep } from "./process";

export type InputArtifact = {
  id: string;
  name: string;
  kind: "video" | "transcript" | "template" | "sop" | "diagram" | "screenshot";
  storagePath: string;
};

export type OutputDocument = {
  id: string;
  kind: "docx";
  storagePath: string;
  exportedAt: string;
};

export type DraftSession = {
  id: string;
  title: string;
  status: "draft" | "processing" | "review" | "exported" | "failed";
  ownerId: string;
  inputArtifacts: InputArtifact[];
  processSteps: ProcessStep[];
  processNotes: ProcessNote[];
  outputDocuments: OutputDocument[];
};

export type ExportResult = {
  id: string;
  kind: string;
  storagePath: string;
  exportedAt: string;
};
