/**
 * Purpose: Custom edge with inline editable label for detailed diagram connectors.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\components\diagram\EditableEdge.tsx
 */

import React from "react";
import { BaseEdge, EdgeLabelRenderer, getSmoothStepPath, type EdgeProps } from "reactflow";

type EditableEdgeData = {
  editable?: boolean;
  selected?: boolean;
  onLabelChange?: (value: string) => void;
};

export function EditableEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  style,
  label,
  data,
}: EdgeProps<EditableEdgeData>): React.JSX.Element {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 18,
    offset: 26,
  });

  const labelText = typeof label === "string" ? label : "";
  const isSelected = Boolean(data?.selected);
  const isEditable = Boolean(data?.editable);

  return (
    <>
      <BaseEdge id={id} path={edgePath} markerEnd={markerEnd} style={style} />
      <EdgeLabelRenderer>
        <div
          className="diagram-edge-label-wrap nodrag nopan"
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: "all",
          }}
        >
          {isSelected && isEditable ? (
            <input
              className="diagram-edge-input"
              value={labelText}
              onChange={(event) => data?.onLabelChange?.(event.target.value)}
              onMouseDown={(event) => event.stopPropagation()}
              onClick={(event) => event.stopPropagation()}
              placeholder="Connector label"
            />
          ) : labelText ? (
            <div className={`diagram-edge-badge${isSelected ? " diagram-edge-badge-selected" : ""}`}>{labelText}</div>
          ) : null}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

export const diagramEdgeTypes = {
  editable: EditableEdge,
};
