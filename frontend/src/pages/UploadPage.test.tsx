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

describe("UploadPage", () => {
  it("shows selected upload counts, pairing guidance, and upload progress state", () => {
    render(
      <UploadPage
        title="Invoice Processing"
        ownerId="kunal"
        diagramType="flowchart"
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
        onTitleChange={vi.fn()}
        onOwnerIdChange={vi.fn()}
        onDiagramTypeChange={vi.fn()}
        onFilesChange={vi.fn()}
        onUploadInputs={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByText("Selected: 2 video(s), 2 transcript(s), 1 template")).toBeInTheDocument();
    expect(screen.getByText(/paired by upload order/i)).toBeInTheDocument();
    expect(screen.getByText("Inputs uploaded")).toBeInTheDocument();
    expect(screen.getByText("1/2 uploaded")).toBeInTheDocument();
    expect(screen.getByText("45%")).toBeInTheDocument();
  });

  it("calls the upload and generate handlers from the default action bar", () => {
    const onUploadInputs = vi.fn();
    const onSubmit = vi.fn();

    render(
      <UploadPage
        title="Invoice Processing"
        ownerId="kunal"
        diagramType="flowchart"
        uploads={createUploads()}
        uploadItems={[]}
        canUploadInputs
        canGenerateDraft
        onTitleChange={vi.fn()}
        onOwnerIdChange={vi.fn()}
        onDiagramTypeChange={vi.fn()}
        onFilesChange={vi.fn()}
        onUploadInputs={onUploadInputs}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Upload inputs" }));
    fireEvent.click(screen.getByRole("button", { name: "Generate Draft" }));

    expect(onUploadInputs).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });
});
