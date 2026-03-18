/**
 * Purpose: Placeholder component for confidence indicators in extracted content.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\components\review\ConfidenceBadge.tsx
 */

import React from "react";

import type { ConfidenceLevel } from "../../types/process";

type ConfidenceBadgeProps = {
  level: ConfidenceLevel;
};

export function ConfidenceBadge({ level }: ConfidenceBadgeProps): React.JSX.Element {
  const label = level.charAt(0).toUpperCase() + level.slice(1);

  return <span className={`confidence-badge ${level}`}>{label} confidence</span>;
}
