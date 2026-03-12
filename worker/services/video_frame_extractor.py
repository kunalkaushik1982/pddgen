r"""
Purpose: Extract candidate screenshot frames from video artifacts using ffmpeg.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\services\video_frame_extractor.py
"""

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess


@dataclass
class ExtractedFrameCandidate:
    """One extracted frame candidate and its sampled timestamp."""

    output_path: str
    timestamp: str
    offset_seconds: int
    file_size: int


class VideoFrameExtractor:
    """Extract timestamp-aligned frames from videos for BA review."""

    def __init__(self) -> None:
        self.ffmpeg_path = shutil.which("ffmpeg")

    def is_available(self) -> bool:
        """Return whether ffmpeg is available on the current machine."""
        return self.ffmpeg_path is not None

    def extract_frame(self, *, video_path: str, output_path: str, timestamp: str) -> bool:
        """Extract a single frame for a timestamp if ffmpeg is available."""
        if not self.ffmpeg_path:
            return False

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.ffmpeg_path,
            "-y",
            "-ss",
            timestamp or "00:00:01",
            "-i",
            video_path,
            "-frames:v",
            "1",
            output_path,
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
        return output.exists()

    def extract_candidate_frames(
        self,
        *,
        video_path: str,
        output_dir: str,
        base_timestamp: str,
        offsets_seconds: list[int],
        filename_prefix: str,
    ) -> list[ExtractedFrameCandidate]:
        """Extract multiple candidate frames around a base timestamp."""
        if not self.ffmpeg_path:
            return []

        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        base_seconds = self._timestamp_to_seconds(base_timestamp or "00:00:01")
        candidates: list[ExtractedFrameCandidate] = []

        for offset in offsets_seconds:
            sample_seconds = max(1, base_seconds + offset)
            sample_timestamp = self._seconds_to_timestamp(sample_seconds)
            output_path = output_root / f"{filename_prefix}_{offset:+d}.png"
            extracted = self.extract_frame(
                video_path=video_path,
                output_path=str(output_path),
                timestamp=sample_timestamp,
            )
            if not extracted:
                continue

            candidates.append(
                ExtractedFrameCandidate(
                    output_path=str(output_path),
                    timestamp=sample_timestamp,
                    offset_seconds=offset,
                    file_size=output_path.stat().st_size if output_path.exists() else 0,
                )
            )
        return candidates

    def extract_frames_at_timestamps(
        self,
        *,
        video_path: str,
        output_dir: str,
        timestamps: list[str],
        filename_prefix: str,
    ) -> list[ExtractedFrameCandidate]:
        """Extract candidate frames for an explicit ordered timestamp list."""
        if not self.ffmpeg_path:
            return []

        output_root = Path(output_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        candidates: list[ExtractedFrameCandidate] = []
        timestamp_list = timestamps or ["00:00:01"]
        base_seconds = self._timestamp_to_seconds(timestamp_list[0])

        for index, sample_timestamp in enumerate(timestamp_list):
            output_path = output_root / f"{filename_prefix}_{index:02d}.png"
            extracted = self.extract_frame(
                video_path=video_path,
                output_path=str(output_path),
                timestamp=sample_timestamp,
            )
            if not extracted:
                continue

            sample_seconds = self._timestamp_to_seconds(sample_timestamp)
            candidates.append(
                ExtractedFrameCandidate(
                    output_path=str(output_path),
                    timestamp=sample_timestamp,
                    offset_seconds=sample_seconds - base_seconds,
                    file_size=output_path.stat().st_size if output_path.exists() else 0,
                )
            )
        return candidates

    @staticmethod
    def _timestamp_to_seconds(timestamp: str) -> int:
        """Convert HH:MM:SS into total seconds."""
        parts = [int(part) for part in timestamp.split(":")]
        while len(parts) < 3:
            parts.insert(0, 0)
        hours, minutes, seconds = parts[-3:]
        return (hours * 3600) + (minutes * 60) + seconds

    @staticmethod
    def _seconds_to_timestamp(total_seconds: int) -> str:
        """Convert total seconds into HH:MM:SS."""
        hours = total_seconds // 3600
        remainder = total_seconds % 3600
        minutes = remainder // 60
        seconds = remainder % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
