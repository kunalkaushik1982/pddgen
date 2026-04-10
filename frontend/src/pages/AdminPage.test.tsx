import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import { AdminPage } from "./AdminPage";

describe("AdminPage metrics column picker", () => {
  it("shows a compact default column set and lets admins toggle extra columns", () => {
    const onVisibleColumnsChange = vi.fn();

    render(
      <AdminPage
        users={[]}
        jobs={[]}
        isLoading={false}
        sessionMetrics={[
          {
            sessionId: "session-1",
            title: "Session One",
            ownerId: "owner-1",
            status: "review",
            updatedAt: "2026-04-10T00:00:00Z",
            llmCallCount: 2,
            totalPromptTokens: 100,
            totalCompletionTokens: 50,
            totalTokensReported: 150,
            estimatedCostUsd: 0.01,
            actualAiCostInr: 1,
            chargeInrWithMargin: 2,
            processingCostInr: 3,
            storageBytesTotal: 1024,
            storageCostInr: 4,
            totalEstimatedCostInr: 5,
            draftGenerationSecondsTotal: 10,
            draftGenerationRuns: 1,
            screenshotGenerationSecondsTotal: 20,
            screenshotGenerationRuns: 2,
          },
        ]}
        visibleMetricColumns={["session", "owner", "status", "total_estimated_cost_inr", "updated_at"]}
        onVisibleMetricColumnsChange={onVisibleColumnsChange}
        ownerOptions={[]}
        selectedOwnerId="all"
        isAdminView
      />,
    );

    expect(screen.getByRole("columnheader", { name: "Session" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Owner" })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "LLM calls" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Columns" }));
    fireEvent.click(screen.getByLabelText("LLM calls"));

    expect(onVisibleColumnsChange).toHaveBeenCalledWith([
      "session",
      "owner",
      "status",
      "total_estimated_cost_inr",
      "updated_at",
      "llm_call_count",
    ]);
  });
});
