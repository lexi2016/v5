"""Frozen M12 Review Core ProducerConfig dependency."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProducerConfig:
    data_root: Path
    source_root: Path | None = None
    funasr_path: Path | None = None
    ffmpeg_path: Path | None = None
    ytdlp_path: Path | None = None
    python_path: Path | None = None
    target_mid: str = "3546557003598528"
    target_uploader: str = "比巴卜作手"
    public_base_url: str = "https://www.bilibili.com"
    network_allowed: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "data_root", Path(self.data_root).absolute())

    def fingerprint(self) -> dict[str, Any]:
        return {"data_root": str(self.data_root), "network_allowed": bool(self.network_allowed), "extra": str(self.extra)}
