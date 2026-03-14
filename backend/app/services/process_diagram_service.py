r"""
Purpose: Build Mermaid process flow definitions and optional rendered diagram assets for PDD export.
Full filepath: C:\Users\work\Documents\PddGenerator\backend\app\services\process_diagram_service.py
"""

import re
import shutil
import subprocess
from pathlib import Path


class ProcessDiagramService:
    """Generate Mermaid flow definitions and render them locally when Mermaid CLI is available."""

    def build_mermaid_flowchart(self, draft_session) -> str:
        """Create a business-level Mermaid flowchart from ordered process steps."""
        ordered_steps = sorted(draft_session.process_steps, key=lambda item: item.step_number)
        if not ordered_steps:
            return "flowchart TD\n    EMPTY[No process steps available]"

        grouped_nodes = self._group_steps_into_business_nodes(ordered_steps)
        lines = [
            "%%{init: {\"theme\": \"neutral\", \"themeVariables\": {\"fontSize\": \"10px\"}, \"flowchart\": {\"nodeSpacing\": 12, \"rankSpacing\": 18, \"curve\": \"basis\"}}}%%",
            "flowchart TD",
        ]
        previous_node_id = ""
        for node_index, node in enumerate(grouped_nodes, start=1):
            node_id = f"B{node_index}"
            label = self._build_business_label(node["title"], node["step_range"])
            shape_open = "{" if node["is_decision"] else "["
            shape_close = "}" if node["is_decision"] else "]"
            lines.append(f"    {node_id}{shape_open}{label}{shape_close}")
            if previous_node_id:
                lines.append(f"    {previous_node_id} --> {node_id}")
            previous_node_id = node_id
        return "\n".join(lines)

    def render_mermaid_diagram(self, mermaid_source: str, output_image_path: Path) -> Path | None:
        """Render Mermaid source into a PNG image when Mermaid CLI is available locally."""
        mermaid_cli = shutil.which("mmdc")
        if not mermaid_cli:
            return None

        output_image_path.parent.mkdir(parents=True, exist_ok=True)
        input_path = output_image_path.with_suffix(".mmd")
        input_path.write_text(mermaid_source, encoding="utf-8")

        try:
            subprocess.run(
                [
                    mermaid_cli,
                    "-i",
                    str(input_path),
                    "-o",
                    str(output_image_path),
                    "-b",
                    "transparent",
                    "-t",
                    "neutral",
                    "-w",
                    "1600",
                    "-H",
                    "1000",
                    "-s",
                    "1",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception:
            return None
        return output_image_path if output_image_path.exists() else None

    def build_to_be_suggestions(self, draft_session) -> list[dict[str, str]]:
        """Create lightweight TO-BE suggestions from extracted steps and notes."""
        suggestions: list[dict[str, str]] = []
        seen_titles: set[str] = set()

        for note in draft_session.process_notes:
            title = self._suggestion_title_from_note(note.text)
            if title in seen_titles:
                continue
            seen_titles.add(title)
            suggestions.append(
                {
                    "title": title,
                    "recommendation": self._suggestion_body_from_note(note.text),
                }
            )

        if not suggestions:
            suggestions.append(
                {
                    "title": "Review Candidate for Automation",
                    "recommendation": "Review the AS-IS steps and identify repeatable, rule-based steps that can move into the TO-BE automated workflow.",
                }
            )

        return suggestions[:5]

    @staticmethod
    def _sanitize_label(value: str) -> str:
        compact = re.sub(r"\s+", " ", value).strip()
        return compact.replace('"', "'")

    @classmethod
    def _build_step_label(cls, step_number: int, action_text: str) -> str:
        compact = cls._sanitize_label(action_text)
        shortened = cls._shorten_text(compact, max_words=5)
        wrapped = cls._wrap_label(shortened, max_line_length=16, max_lines=2)
        return cls._sanitize_label(f"Step {step_number}<br/>{wrapped}")

    @classmethod
    def _build_business_label(cls, title: str, step_range: str) -> str:
        wrapped = cls._wrap_label(title, max_line_length=18, max_lines=3)
        return cls._sanitize_label(f"{wrapped}<br/><sub>{step_range}</sub>")

    @staticmethod
    def _shorten_text(value: str, max_words: int) -> str:
        words = value.split()
        if len(words) <= max_words:
            return value
        return " ".join(words[:max_words]) + " ..."

    @staticmethod
    def _wrap_label(value: str, max_line_length: int, max_lines: int) -> str:
        words = value.split()
        if not words:
            return value

        lines: list[str] = []
        current_line = ""
        for word in words:
            candidate = f"{current_line} {word}".strip()
            if len(candidate) <= max_line_length or not current_line:
                current_line = candidate
                continue
            lines.append(current_line)
            current_line = word
            if len(lines) == max_lines - 1:
                break

        used_word_count = len(" ".join(lines).split())
        remaining_words = words[used_word_count:]
        if current_line:
            remaining_line_words = [current_line, *remaining_words]
            lines.append(" ".join(item for item in remaining_line_words if item))

        lines = lines[:max_lines]
        if lines and len(lines[-1]) > max_line_length:
            lines[-1] = lines[-1][: max_line_length - 4].rstrip() + " ..."
        return "<br/>".join(line.strip() for line in lines if line.strip())

    @staticmethod
    def _looks_like_decision(action_text: str) -> bool:
        lowered = action_text.lower()
        return any(keyword in lowered for keyword in ["if ", "whether", "validate", "check", "verify"])

    def _group_steps_into_business_nodes(self, ordered_steps) -> list[dict[str, str | bool]]:
        groups: list[dict[str, object]] = []

        for step in ordered_steps:
            bucket_title = self._business_bucket_title(step.action_text)
            if groups and groups[-1]["title"] == bucket_title:
                groups[-1]["steps"].append(step)
                continue
            groups.append({"title": bucket_title, "steps": [step]})

        business_nodes: list[dict[str, str | bool]] = []
        for group in groups:
            steps = group["steps"]
            first_step = steps[0]
            last_step = steps[-1]
            step_range = (
                f"Step {first_step.step_number}"
                if first_step.step_number == last_step.step_number
                else f"Steps {first_step.step_number}-{last_step.step_number}"
            )
            business_nodes.append(
                {
                    "title": str(group["title"]),
                    "step_range": step_range,
                    "is_decision": any(self._looks_like_decision(step.action_text) for step in steps),
                }
            )
        return business_nodes

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
    def _suggestion_title_from_note(note_text: str) -> str:
        lowered = note_text.lower()
        if "mandatory" in lowered or "must" in lowered:
            return "Strengthen Mandatory Field Validation"
        if "check" in lowered or "validate" in lowered:
            return "Automate Validation Checks"
        if "copy" in lowered or "paste" in lowered:
            return "Reduce Manual Data Movement"
        return "Improve Future-State Control"

    @staticmethod
    def _suggestion_body_from_note(note_text: str) -> str:
        return f"Suggested TO-BE improvement: {note_text}"
