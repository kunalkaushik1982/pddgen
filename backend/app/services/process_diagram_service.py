r"""
Purpose: Build diagram models and render flowchart assets for PDD export.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\process_diagram_service.py
"""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


class ProcessDiagramService:
    """Generate preview and export diagram data."""

    NODE_WIDTH = 220
    NODE_HEIGHT = 84
    DECISION_SIZE = 160
    COLUMN_GAP = 52
    ROW_GAP = 120
    NODES_PER_ROW = 4

    def build_diagram_model(self, draft_session, view_type: str, process_group_id: str | None = None) -> dict:
        scoped_session = self._scope_session(draft_session, process_group_id)
        stored = self._load_stored_diagram_model(scoped_session, view_type)
        if stored is not None:
            return stored
        if view_type == "detailed":
            return self.build_detailed_flowchart_model(scoped_session)
        return self.build_flowchart_model(scoped_session)

    def build_flowchart_model(self, draft_session) -> dict:
        normalized_steps = self._build_normalized_detailed_steps(draft_session)
        grouped = self._build_overview_business_nodes(normalized_steps)
        nodes = [
            {
                "id": f"n{index}",
                "label": node["title"],
                "category": "decision" if node["is_decision"] else "process",
                "step_range": node["step_range"],
            }
            for index, node in enumerate(grouped, start=1)
        ]
        edges = [
            {"id": f"e{index}", "source": f"n{index}", "target": f"n{index + 1}", "label": ""}
            for index in range(1, len(nodes))
        ]
        if not nodes:
            nodes = [{"id": "n1", "label": "No process steps available", "category": "empty", "step_range": ""}]
        return {
            "diagram_type": "flowchart",
            "view_type": "overview",
            "title": draft_session.title,
            "nodes": nodes,
            "edges": edges,
        }

    def build_detailed_flowchart_model(self, draft_session) -> dict:
        normalized_steps = self._build_normalized_detailed_steps(draft_session)
        if not normalized_steps:
            return {
                "diagram_type": "flowchart",
                "view_type": "detailed",
                "title": draft_session.title,
                "nodes": [{"id": "n1", "label": "No process steps available", "category": "empty", "step_range": ""}],
                "edges": [],
            }

        nodes: list[dict[str, str]] = []
        edges: list[dict[str, str]] = []
        node_ids = [f"s{index}" for index in range(1, len(normalized_steps) + 1)]

        for index, step in enumerate(normalized_steps, start=1):
            step_id = node_ids[index - 1]
            next_id = node_ids[index] if index < len(node_ids) else ""
            nodes.append(
                {
                    "id": step_id,
                    "label": self._shorten(step["label"], 10),
                    "category": "decision" if step["is_decision"] else "process",
                    "step_range": step["step_range"],
                }
            )
            if next_id:
                edges.append({"id": f"e{step_id}-{next_id}", "source": step_id, "target": next_id, "label": ""})

        return {
            "diagram_type": "flowchart",
            "view_type": "detailed",
            "title": draft_session.title,
            "nodes": nodes,
            "edges": edges,
        }

    def build_diagram_source(self, draft_session) -> str:
        if (draft_session.diagram_type or "flowchart").lower() == "sequence":
            return self.build_mermaid_sequence_diagram(draft_session)
        return json.dumps(self.build_flowchart_model(draft_session), ensure_ascii=True, indent=2)

    def _scope_session(self, draft_session, process_group_id: str | None):
        if not process_group_id:
            return draft_session

        matched_group = next((group for group in getattr(draft_session, "process_groups", []) if group.id == process_group_id), None)
        scoped_title = matched_group.title if matched_group and getattr(matched_group, "title", "") else draft_session.title

        class ScopedSession:
            pass

        scoped = ScopedSession()
        scoped.id = draft_session.id
        scoped.title = scoped_title
        scoped.diagram_type = draft_session.diagram_type
        scoped.process_steps = [step for step in getattr(draft_session, "process_steps", []) if getattr(step, "process_group_id", None) == process_group_id]
        scoped.process_notes = [note for note in getattr(draft_session, "process_notes", []) if getattr(note, "process_group_id", None) == process_group_id]
        scoped.diagram_layouts = [
            layout
            for layout in getattr(draft_session, "diagram_layouts", [])
            if getattr(layout, "process_group_id", None) == process_group_id
        ]
        if matched_group is not None:
            scoped.overview_diagram_json = getattr(matched_group, "overview_diagram_json", "") or ""
            scoped.detailed_diagram_json = getattr(matched_group, "detailed_diagram_json", "") or ""
        else:
            scoped.overview_diagram_json = ""
            scoped.detailed_diagram_json = ""
        return scoped

    def _load_stored_diagram_model(self, draft_session, view_type: str) -> dict | None:
        raw_value = draft_session.detailed_diagram_json if view_type == "detailed" else draft_session.overview_diagram_json
        if not raw_value:
            return None
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        nodes = parsed.get("nodes", [])
        edges = parsed.get("edges", [])
        if not isinstance(nodes, list) or not isinstance(edges, list):
            return None
        return {
            "diagram_type": str(parsed.get("diagram_type", "flowchart") or "flowchart"),
            "view_type": str(parsed.get("view_type", view_type) or view_type),
            "title": str(parsed.get("title", draft_session.title) or draft_session.title),
            "nodes": nodes,
            "edges": edges,
        }

    def render_flowchart_view(
        self,
        draft_session,
        view_type: str,
        output_path: Path,
        saved_positions: dict[str, dict[str, float]] | None = None,
        process_group_id: str | None = None,
    ) -> Path | None:
        layout = self.build_export_layout(
            draft_session,
            view_type,
            saved_positions=saved_positions,
            process_group_id=process_group_id,
        )
        return self._draw_png(layout, output_path)

    def render_sequence_diagram(self, draft_session, output_path: Path) -> Path | None:
        mermaid_cli = shutil.which("mmdc")
        if not mermaid_cli:
            return None
        source = self.build_mermaid_sequence_diagram(draft_session)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        input_path = output_path.with_suffix(".mmd")
        input_path.write_text(source, encoding="utf-8")
        try:
            subprocess.run(
                [mermaid_cli, "-i", str(input_path), "-o", str(output_path), "-b", "transparent", "-t", "neutral", "-w", "1600", "-H", "1000", "-s", "1"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception:
            return None
        return output_path if output_path.exists() else None

    def build_export_layout(
        self,
        draft_session,
        view_type: str,
        saved_positions: dict[str, dict[str, float]] | None = None,
        process_group_id: str | None = None,
    ) -> dict:
        model = self.build_diagram_model(draft_session, view_type, process_group_id=process_group_id)
        layout = self._build_detailed_layout(model) if view_type == "detailed" else self._build_overview_layout(model)
        saved = saved_positions if saved_positions is not None else self._load_saved_positions(draft_session, view_type)
        for node in layout["nodes"]:
            if node["id"] in saved:
                node["x"] = saved[node["id"]]["x"]
                node["y"] = saved[node["id"]]["y"]
                if saved[node["id"]].get("label"):
                    node["label"] = str(saved[node["id"]]["label"])
        return layout

    def build_to_be_suggestions(self, draft_session) -> list[dict[str, str]]:
        suggestions: list[dict[str, str]] = []
        seen_titles: set[str] = set()
        for note in draft_session.process_notes:
            title = self._suggestion_title(note.text)
            if title in seen_titles:
                continue
            seen_titles.add(title)
            suggestions.append({"title": title, "recommendation": f"Suggested TO-BE improvement: {note.text}"})
        if not suggestions:
            suggestions.append(
                {
                    "title": "Review Candidate for Automation",
                    "recommendation": "Review the AS-IS steps and identify repeatable, rule-based steps that can move into the TO-BE automated workflow.",
                }
            )
        return suggestions[:5]

    def build_mermaid_sequence_diagram(self, draft_session) -> str:
        ordered_steps = sorted(draft_session.process_steps, key=lambda item: item.step_number)
        participants = ["User"]
        for step in ordered_steps:
            participant = self._participant_name(step.application_name)
            if participant not in participants:
                participants.append(participant)
        lines = ["%%{init: {\"theme\": \"neutral\", \"themeVariables\": {\"fontSize\": \"11px\"}}}%%", "sequenceDiagram"]
        for participant in participants:
            lines.append(f"    participant {participant} as {participant}")
        previous_actor = participants[0] if participants else "User"
        for step in ordered_steps:
            current_actor = self._participant_name(step.application_name)
            action = self._sanitize(self._shorten(step.action_text, 8))
            lines.append(f"    {previous_actor}->>{current_actor}: Step {step.step_number} {action}")
            previous_actor = current_actor
        return "\n".join(lines)

    def _build_overview_layout(self, model: dict) -> dict:
        nodes = []
        for index, node in enumerate(model["nodes"]):
            row = index // self.NODES_PER_ROW
            col = index % self.NODES_PER_ROW
            reverse = row % 2 == 1
            visual_col = self.NODES_PER_ROW - 1 - col if reverse else col
            category = "start" if index == 0 else node["category"]
            nodes.append(
                {
                    "id": node["id"],
                    "label": f"Start\n{node['label']}" if index == 0 else node["label"],
                    "step_range": node["step_range"],
                    "category": category,
                    "x": visual_col * (self.NODE_WIDTH + self.COLUMN_GAP),
                    "y": row * self.ROW_GAP,
                    "width": self.DECISION_SIZE if category == "decision" else self.NODE_WIDTH,
                    "height": self.DECISION_SIZE if category == "decision" else self.NODE_HEIGHT,
                }
            )
        return {"title": model["title"], "view_type": model["view_type"], "nodes": nodes, "edges": model["edges"]}

    def _build_detailed_layout(self, model: dict) -> dict:
        positions: dict[str, dict[str, float]] = {}
        center_x = 470.0
        current_y = 0.0
        vertical_gap = 180.0
        node_ids = [node["id"] for node in model["nodes"]]
        for node_id in node_ids:
            positions[node_id] = {"x": center_x, "y": current_y}
            current_y += vertical_gap
        nodes = []
        for index, node in enumerate(model["nodes"]):
            category = "start" if index == 0 else node["category"]
            pos = positions.get(node["id"], {"x": center_x, "y": index * 180.0})
            nodes.append(
                {
                    "id": node["id"],
                    "label": f"Start\n{node['label']}" if index == 0 else node["label"],
                    "step_range": node["step_range"],
                    "category": category,
                    "x": pos["x"],
                    "y": pos["y"],
                    "width": self.DECISION_SIZE if category == "decision" else self.NODE_WIDTH,
                    "height": self.DECISION_SIZE if category == "decision" else self.NODE_HEIGHT,
                }
            )
        return {"title": model["title"], "view_type": model["view_type"], "nodes": nodes, "edges": model["edges"]}

    def _load_saved_positions(self, draft_session, view_type: str) -> dict[str, dict[str, float | str]]:
        for layout in getattr(draft_session, "diagram_layouts", []):
            if layout.view_type != view_type:
                continue
            try:
                parsed = json.loads(layout.layout_json or "[]")
            except json.JSONDecodeError:
                return {}
            items = parsed.get("nodes", []) if isinstance(parsed, dict) else parsed
            result: dict[str, dict[str, float | str]] = {}
            for item in items:
                node_id = item.get("id")
                if node_id:
                    result[node_id] = {
                        "x": float(item.get("x", 0)),
                        "y": float(item.get("y", 0)),
                        "label": str(item.get("label", "")) if item.get("label") else "",
                    }
            return result
        return {}

    def _draw_png(self, layout: dict, output_path: Path) -> Path | None:
        if not layout["nodes"]:
            return None
        scale = 3
        padding = 80
        min_x = min(node["x"] for node in layout["nodes"])
        min_y = min(node["y"] for node in layout["nodes"])
        max_x = max(node["x"] + node["width"] for node in layout["nodes"])
        max_y = max(node["y"] + node["height"] for node in layout["nodes"])
        x_offset = padding - min_x
        y_offset = padding - min_y
        image = Image.new("RGB", (max(int((max_x - min_x + padding * 2) * scale), 1600), max(int((max_y - min_y + padding * 2) * scale), 1200)), "white")
        draw = ImageDraw.Draw(image)
        body_font = self._font(54)
        small_font = self._font(42)
        edge_font = self._font(36)
        node_map = {node["id"]: node for node in layout["nodes"]}
        for edge in layout["edges"]:
            source = node_map.get(edge["source"])
            target = node_map.get(edge["target"])
            if source and target:
                self._draw_edge(draw, source, target, edge["label"], x_offset, y_offset, scale, edge_font)
        for node in layout["nodes"]:
            self._draw_node(draw, node, x_offset, y_offset, scale, body_font, small_font)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path, format="PNG", optimize=True)
        return output_path

    def _draw_node(self, draw: ImageDraw.ImageDraw, node: dict, x_offset: float, y_offset: float, scale: int, body_font, small_font) -> None:
        left = int((node["x"] + x_offset) * scale)
        top = int((node["y"] + y_offset) * scale)
        width = int(node["width"] * scale)
        height = int(node["height"] * scale)
        right = left + width
        bottom = top + height
        outline = "#8C67F3"
        if node["category"] == "start":
            outline = "#6FF3B5"
        elif node["category"] == "terminal":
            outline = "#FFB366"
        if node["category"] == "decision":
            cx = left + width // 2
            cy = top + height // 2
            draw.polygon([(cx, top), (right, cy), (cx, bottom), (left, cy)], fill="#261C43", outline=outline, width=6)
            box = (left + 78, top + 78, right - 78, bottom - 78)
        else:
            draw.rounded_rectangle((left, top, right, bottom), radius=54, fill="#261C43", outline=outline, width=6)
            box = (left + 54, top + 48, right - 54, bottom - 48)
        title_lines = self._wrap(draw, node["label"], body_font, box[2] - box[0], 3)
        range_lines = self._wrap(draw, node["step_range"], small_font, box[2] - box[0], 1) if node["step_range"] else []
        title_height = self._text_height(draw, title_lines, body_font)
        range_height = self._text_height(draw, range_lines, small_font) if range_lines else 0
        current_y = box[1] + max(0, ((box[3] - box[1]) - (title_height + range_height + (30 if range_lines else 0))) // 2)
        self._draw_centered(draw, title_lines, body_font, "#F4EEFF", box, current_y)
        if range_lines:
            self._draw_centered(draw, range_lines, small_font, "#CDBBFF", box, current_y + title_height + 30)

    def _draw_edge(self, draw: ImageDraw.ImageDraw, source: dict, target: dict, label: str, x_offset: float, y_offset: float, scale: int, edge_font) -> None:
        sx = (source["x"] + source["width"] / 2 + x_offset) * scale
        sy_top = (source["y"] + y_offset) * scale
        sy_bottom = (source["y"] + source["height"] + y_offset) * scale
        sy_mid = (source["y"] + source["height"] / 2 + y_offset) * scale
        sx_left = (source["x"] + x_offset) * scale
        sx_right = (source["x"] + source["width"] + x_offset) * scale
        tx = (target["x"] + target["width"] / 2 + x_offset) * scale
        ty_top = (target["y"] + y_offset) * scale
        ty_bottom = (target["y"] + target["height"] + y_offset) * scale
        ty_mid = (target["y"] + target["height"] / 2 + y_offset) * scale
        tx_left = (target["x"] + x_offset) * scale
        tx_right = (target["x"] + target["width"] + x_offset) * scale
        if label == "No":
            points = [(sx_left, sy_mid), (sx_left - 180, sy_mid), (sx_left - 180, ty_mid), (tx_right, ty_mid)]
            label_point = (sx_left - 144, sy_mid - 60)
        elif label == "Yes":
            points = [(sx_right, sy_mid), (sx_right + 180, sy_mid), (sx_right + 180, ty_top - 72), (tx, ty_top)]
            label_point = (sx_right + 72, sy_mid - 60)
        else:
            if source["category"] == "decision" or target["category"] == "decision":
                points = self._build_general_route((sx, sy_mid), (tx, ty_mid), source, target, x_offset, y_offset, scale, sx_left, sx_right, sy_top, sy_bottom, tx_left, tx_right, ty_top, ty_bottom)
            else:
                points = self._build_general_route((sx, sy_mid), (tx, ty_mid), source, target, x_offset, y_offset, scale, sx_left, sx_right, sy_top, sy_bottom, tx_left, tx_right, ty_top, ty_bottom)
            label_point = None
        draw.line(points, fill="#8C67F3", width=6)
        self._arrow(draw, points[-2], points[-1])
        if label and label_point:
            bbox = draw.textbbox((0, 0), label, font=edge_font)
            rect = (label_point[0] - 18, label_point[1] - 12, label_point[0] + (bbox[2] - bbox[0]) + 18, label_point[1] + (bbox[3] - bbox[1]) + 12)
            draw.rounded_rectangle(rect, radius=18, fill="white", outline="#8C67F3", width=3)
            draw.text(label_point, label, font=edge_font, fill="#4B3A72")

    @staticmethod
    def _build_general_route(
        source_center: tuple[float, float],
        target_center: tuple[float, float],
        source: dict,
        target: dict,
        x_offset: float,
        y_offset: float,
        scale: int,
        sx_left: float,
        sx_right: float,
        sy_top: float,
        sy_bottom: float,
        tx_left: float,
        tx_right: float,
        ty_top: float,
        ty_bottom: float,
    ) -> list[tuple[float, float]]:
        dx = target_center[0] - source_center[0]
        dy = target_center[1] - source_center[1]
        if abs(dx) >= abs(dy):
            if dx >= 0:
                start = (sx_right, source_center[1])
                end = (tx_left, target_center[1])
                mid_x = (start[0] + end[0]) / 2
                return [start, (mid_x, start[1]), (mid_x, end[1]), end]
            start = (sx_left, source_center[1])
            end = (tx_right, target_center[1])
            mid_x = (start[0] + end[0]) / 2
            return [start, (mid_x, start[1]), (mid_x, end[1]), end]

        if dy >= 0:
            start = (source_center[0], sy_bottom)
            end = (target_center[0], ty_top)
            mid_y = (start[1] + end[1]) / 2
            return [start, (start[0], mid_y), (end[0], mid_y), end]
        start = (source_center[0], sy_top)
        end = (target_center[0], ty_bottom)
        mid_y = (start[1] + end[1]) / 2
        return [start, (start[0], mid_y), (end[0], mid_y), end]

    def _arrow(self, draw: ImageDraw.ImageDraw, start: tuple[float, float], end: tuple[float, float]) -> None:
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        size = 30
        left = (end[0] - size * math.cos(angle - math.pi / 6), end[1] - size * math.sin(angle - math.pi / 6))
        right = (end[0] - size * math.cos(angle + math.pi / 6), end[1] - size * math.sin(angle + math.pi / 6))
        draw.polygon([end, left, right], fill="#8C67F3")

    @staticmethod
    def _font(size: int):
        for candidate in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/calibri.ttf"):
            path = Path(candidate)
            if path.exists():
                try:
                    return ImageFont.truetype(str(path), size=size)
                except Exception:
                    continue
        return ImageFont.load_default()

    @staticmethod
    def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, max_lines: int) -> list[str]:
        if not text:
            return []
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if bbox[2] - bbox[0] <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
                if len(lines) == max_lines - 1:
                    break
        if current:
            lines.append(current)
        lines = lines[:max_lines]
        if lines:
            bbox = draw.textbbox((0, 0), lines[-1], font=font)
            while bbox[2] - bbox[0] > max_width and len(lines[-1]) > 4:
                lines[-1] = lines[-1][:-4].rstrip() + " ..."
                bbox = draw.textbbox((0, 0), lines[-1], font=font)
        return lines

    @staticmethod
    def _text_height(draw: ImageDraw.ImageDraw, lines: list[str], font) -> int:
        return sum(draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] for line in lines) + max(0, len(lines) - 1) * 18

    @staticmethod
    def _draw_centered(draw: ImageDraw.ImageDraw, lines: list[str], font, fill: str, box: tuple[int, int, int, int], start_y: int) -> None:
        current_y = start_y
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            x = box[0] + max(0, ((box[2] - box[0]) - (bbox[2] - bbox[0])) // 2)
            draw.text((x, current_y), line, font=font, fill=fill)
            current_y += (bbox[3] - bbox[1]) + 18

    @staticmethod
    def _sanitize(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip().replace('"', "'")

    @staticmethod
    def _shorten(value: str, max_words: int) -> str:
        words = value.split()
        return value if len(words) <= max_words else " ".join(words[:max_words]) + " ..."

    @staticmethod
    def _looks_like_decision(action_text: str) -> bool:
        lowered = action_text.lower()
        return any(keyword in lowered for keyword in ["if ", "whether", "validate", "check", "verify", "otherwise", "else", "if not", "in case"])

    def _build_normalized_detailed_steps(self, draft_session) -> list[dict[str, str | bool]]:
        ordered_steps = sorted(draft_session.process_steps, key=lambda item: item.step_number)
        normalized: list[dict[str, str | bool]] = []

        for step in ordered_steps:
            action_text = self._sanitize(step.action_text)
            if not action_text:
                continue

            normalized_label = self._normalize_action_label(action_text)
            evidence_text = " ".join(
                part
                for part in [action_text, getattr(step, "supporting_transcript_text", "") or "", getattr(step, "source_data_note", "") or ""]
                if part
            )
            is_decision = self._looks_like_decision(evidence_text)

            if normalized and normalized[-1]["normalized_key"] == normalized_label.lower() and normalized[-1]["is_decision"] == is_decision:
                normalized[-1]["last_step_number"] = step.step_number
                normalized[-1]["step_range"] = self._format_step_range(
                    int(normalized[-1]["first_step_number"]),
                    int(normalized[-1]["last_step_number"]),
                )
                continue

            normalized.append(
                {
                    "label": normalized_label,
                    "normalized_key": normalized_label.lower(),
                    "is_decision": is_decision,
                    "first_step_number": step.step_number,
                    "last_step_number": step.step_number,
                    "step_range": self._format_step_range(step.step_number, step.step_number),
                }
            )

        return normalized

    def _build_overview_business_nodes(self, ordered_steps) -> list[dict[str, str | bool]]:
        grouped_by_title: dict[str, dict[str, object]] = {}
        ordered_titles: list[str] = []

        for step in ordered_steps:
            bucket_title = self._business_bucket_title(str(step["label"]))
            if bucket_title not in grouped_by_title:
                grouped_by_title[bucket_title] = {"steps": [], "title": bucket_title}
                ordered_titles.append(bucket_title)
            grouped_by_title[bucket_title]["steps"].append(step)

        business_nodes: list[dict[str, str | bool]] = []
        for title in ordered_titles:
            steps = grouped_by_title[title]["steps"]
            first_step = steps[0]
            last_step = steps[-1]
            step_range = self._format_step_range(int(first_step["first_step_number"]), int(last_step["last_step_number"]))
            business_nodes.append(
                {
                    "title": str(title),
                    "step_range": step_range,
                    "is_decision": any(bool(step["is_decision"]) for step in steps),
                }
            )
        return business_nodes

    @staticmethod
    def _format_step_range(first_step_number: int, last_step_number: int) -> str:
        return f"Step {first_step_number}" if first_step_number == last_step_number else f"Steps {first_step_number}-{last_step_number}"

    def _normalize_action_label(self, action_text: str) -> str:
        label = re.sub(r"\s+", " ", action_text).strip()
        label = re.sub(r"^(then|next|after that|now)\s+", "", label, flags=re.IGNORECASE)
        return label[:1].upper() + label[1:] if label else label

    @staticmethod
    def _business_bucket_title(action_text: str) -> str:
        lowered = action_text.lower()
        if any(keyword in lowered for keyword in ["open", "launch", "start", "access"]):
            return "Open Process Screen"
        if any(keyword in lowered for keyword in ["organization", "purchasing group", "company", "plant"]):
            return "Enter Organizational Details"
        if any(keyword in lowered for keyword in ["vendor", "supplier"]):
            return "Select Supplier"
        if any(keyword in lowered for keyword in ["material", "item", "quantity", "delivery", "storage location"]):
            return "Enter Item and Delivery Details"
        if any(keyword in lowered for keyword in ["validate", "check", "verify"]):
            return "Validate Purchase Order"
        if any(keyword in lowered for keyword in ["save", "create", "submit"]):
            return "Save Purchase Order"
        if any(keyword in lowered for keyword in ["display", "review", "open po", "me23n"]):
            return "Review Created Purchase Order"
        return "Complete Process Step"

    @staticmethod
    def _participant_name(application_name: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9]+", "", application_name or "System")
        return cleaned or "System"

    @staticmethod
    def _suggestion_title(note_text: str) -> str:
        lowered = note_text.lower()
        if "mandatory" in lowered or "must" in lowered:
            return "Strengthen Mandatory Field Validation"
        if "check" in lowered or "validate" in lowered:
            return "Automate Validation Checks"
        if "copy" in lowered or "paste" in lowered:
            return "Reduce Manual Data Movement"
        return "Improve Future-State Control"
