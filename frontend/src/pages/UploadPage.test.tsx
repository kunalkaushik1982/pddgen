import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import { UploadPage } from "./UploadPage";
import type { ArtifactUploadState } from "../types/workflow";

function createUploads(): ArtifactUploadState {
  return {
    videoFiles: [new File(["video-a"], "walkthrough-1.mp4"), new File(["video-b"], "walkthrough-2.mp4")],
    transcriptFiles: [new File(["transcript-a"], "transcript-1.docx"), new File(["transcript-b"], "transcript-2.docx")],
    templateFile: new File(["template"], "pdd-template.docx"),
    optionalArtifacts: {
      sopFiles: [],
      diagramFiles: [],
    },
  };
}

/** Upload state with no video files — video is optional. */
function createUploadsNoVideo(): ArtifactUploadState {
  return {
    videoFiles: [],
    transcriptFiles: [new File(["transcript-a"], "transcript-1.docx")],
    templateFile: new File(["template"], "pdd-template.docx"),
    optionalArtifacts: {
      sopFiles: [],
      diagramFiles: [],
    },
  };
}

const baseProps = {
  title: "Invoice Processing",
  ownerId: "kunal",
  diagramType: "flowchart" as const,
  onTitleChange: vi.fn(),
  onOwnerIdChange: vi.fn(),
  onDiagramTypeChange: vi.fn(),
  onFilesChange: vi.fn(),
  onSubmit: vi.fn(),
};

describe("UploadPage", () => {
  it("shows selected upload counts, pairing guidance, and upload progress state", () => {
    render(
      <UploadPage
        {...baseProps}
        uploads={createUploads()}
        uploadItems={[
          {
            key: "video-1",
            artifactKind: "video",
            name: "walkthrough-1.mp4",
            size: 1024,
            status: "uploaded",
            progress: 100,
            error: null,
          },
          {
            key: "transcript-1",
            artifactKind: "transcript",
            name: "transcript-1.docx",
            size: 2048,
            status: "uploading",
            progress: 45,
            error: null,
          },
        ]}
        uploadReady
        canUploadInputs
        canGenerateDraft
        onRemoveSelectedFile={vi.fn()}
        onUploadInputs={vi.fn()}
      />,
    );

    expect(screen.getByText(/2 video\(s\)/i)).toBeInTheDocument();
    expect(screen.getByText(/2 transcript\(s\)/i)).toBeInTheDocument();
    expect(screen.getByText("Inputs uploaded")).toBeInTheDocument();
    // Combined video(100%) + transcript(45%) = avg 72.5% → rounds to 73%
    expect(screen.getByText("Uploading 73%")).toBeInTheDocument();
  });

  it("calls the upload and generate handlers from the default action bar", () => {
    const onUploadInputs = vi.fn();
    const onSubmit = vi.fn();

    render(
      <UploadPage
        {...baseProps}
        uploads={createUploads()}
        uploadItems={[]}
        canUploadInputs
        canGenerateDraft
        onUploadInputs={onUploadInputs}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Upload inputs" }));
    fireEvent.click(screen.getByRole("button", { name: "Generate Draft" }));

    expect(onUploadInputs).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("renders correctly with no video files — video is optional", () => {
    render(
      <UploadPage
        {...baseProps}
        uploads={createUploadsNoVideo()}
        uploadItems={[]}
        canUploadInputs
        canGenerateDraft={false}
        onUploadInputs={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    // The "(optional)" badge should appear on the video field label
    expect(screen.getByText("(optional)")).toBeInTheDocument();

    // The hint text should appear
    expect(screen.getByText(/without a video, screenshots will be skipped/i)).toBeInTheDocument();

    // Count summary should mention 0 videos without treating it as an error
    expect(screen.getByText(/0 video\(s\)/i)).toBeInTheDocument();
    // Should reflect no screenshots notice inline
    expect(screen.getByText(/no screenshots without video/i)).toBeInTheDocument();

    // The "Upload inputs" button should still be enabled (transcript + template present)
    expect(screen.getByRole("button", { name: "Upload inputs" })).not.toBeDisabled();
  });

  it("shows the recording videos field labelled as optional", () => {
    render(
      <UploadPage
        {...baseProps}
        uploads={createUploads()}
        uploadItems={[]}
        onSubmit={vi.fn()}
      />,
    );

    // The field label for video must show "(optional)"
    const optionalBadge = screen.getByText("(optional)");
    expect(optionalBadge).toBeInTheDocument();
  });
});
