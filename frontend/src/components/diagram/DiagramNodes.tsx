/**
 * Purpose: Custom React Flow nodes for clearer process and decision rendering.
 * Full filepath: C:\Users\work\Documents\PddGenerator\frontend\src\components\diagram\DiagramNodes.tsx
 */

import React from "react";
import { Handle, NodeResizer, Position, type NodeProps } from "reactflow";

type DiagramNodeData = {
  label: string;
  stepRange: string;
  category: string;
  viewType?: "overview" | "detailed";
  canvasTheme?: "dark" | "light" | "blueprint" | "plain";
  editable?: boolean;
  onLabelChange?: (value: string) => void;
  selected?: boolean;
  connectorSource?: boolean;
};

const HANDLE_OFFSETS = [20, 40, 60, 80];

function SideHandles({ type, side }: { type: "source" | "target"; side: Position }): JSX.Element {
  return (
    <>
      {HANDLE_OFFSETS.map((offset, index) => {
        const style =
          side === Position.Top || side === Position.Bottom
            ? { left: `${offset}%` }
            : { top: `${offset}%` };
        const sideName =
          side === Position.Top ? "top" : side === Position.Bottom ? "bottom" : side === Position.Left ? "left" : "right";
        return <Handle key={`${type}-${sideName}-${index + 1}`} type={type} position={side} id={`${type}-${sideName}-${index + 1}`} style={style} />;
      })}
    </>
  );
}

function LabelContent({ data }: { data: DiagramNodeData }): JSX.Element {
  if (data.editable && data.onLabelChange) {
    return (
      <textarea
        className="diagram-node-input nodrag nopan"
        value={data.label}
        onChange={(event) => data.onLabelChange?.(event.target.value)}
        rows={3}
      />
    );
  }

  return <div className="diagram-node-title">{data.label}</div>;
}

function BaseNode({ data, className }: { data: DiagramNodeData; className: string }): JSX.Element {
  const classes = [className, `diagram-node-theme-${data.canvasTheme ?? "dark"}`];
  if (data.selected) {
    classes.push("diagram-node-selected");
  }
  if (data.connectorSource) {
    classes.push("diagram-node-connector-source");
  }

  return (
    <div className={classes.join(" ")}>
      {data.editable ? (
        <NodeResizer
          isVisible={Boolean(data.selected)}
          minWidth={140}
          minHeight={84}
          lineClassName="diagram-resizer-line"
          handleClassName="diagram-resizer-handle"
        />
      ) : null}
      <SideHandles type="target" side={Position.Top} />
      <SideHandles type="target" side={Position.Bottom} />
      <SideHandles type="target" side={Position.Left} />
      <SideHandles type="target" side={Position.Right} />
      <SideHandles type="source" side={Position.Top} />
      <SideHandles type="source" side={Position.Bottom} />
      <SideHandles type="source" side={Position.Left} />
      <SideHandles type="source" side={Position.Right} />
      <LabelContent data={data} />
      {data.stepRange ? <div className="diagram-node-range">{data.stepRange}</div> : null}
    </div>
  );
}

export function ProcessNode({ data }: NodeProps<DiagramNodeData>): JSX.Element {
  return <BaseNode data={data} className="diagram-node-card" />;
}

export function StartNode({ data }: NodeProps<DiagramNodeData>): JSX.Element {
  return <BaseNode data={data} className="diagram-node-card diagram-node-card-start" />;
}

export function TerminalNode({ data }: NodeProps<DiagramNodeData>): JSX.Element {
  return <BaseNode data={data} className="diagram-node-card diagram-node-card-terminal" />;
}

export function DecisionNode({ data }: NodeProps<DiagramNodeData>): JSX.Element {
  const classes = ["diagram-node-decision-card", `diagram-node-theme-${data.canvasTheme ?? "dark"}`];
  if (data.selected) {
    classes.push("diagram-node-selected");
  }
  if (data.connectorSource) {
    classes.push("diagram-node-connector-source");
  }

  return (
    <div className="diagram-node-decision-wrap">
      {data.editable ? (
        <NodeResizer
          isVisible={Boolean(data.selected)}
          minWidth={160}
          minHeight={160}
          lineClassName="diagram-resizer-line"
          handleClassName="diagram-resizer-handle"
        />
      ) : null}
      <SideHandles type="target" side={Position.Top} />
      <SideHandles type="target" side={Position.Bottom} />
      <SideHandles type="target" side={Position.Left} />
      <SideHandles type="target" side={Position.Right} />
      <SideHandles type="source" side={Position.Top} />
      <SideHandles type="source" side={Position.Bottom} />
      <SideHandles type="source" side={Position.Left} />
      <SideHandles type="source" side={Position.Right} />
      <div className={classes.join(" ")}>
        <LabelContent data={data} />
        {data.stepRange ? <div className="diagram-node-range">{data.stepRange}</div> : null}
      </div>
    </div>
  );
}

export const diagramNodeTypes = {
  process: ProcessNode,
  start: StartNode,
  terminal: TerminalNode,
  decision: DecisionNode,
  empty: ProcessNode,
};
