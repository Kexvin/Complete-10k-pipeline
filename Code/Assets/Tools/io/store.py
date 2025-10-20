from __future__ import annotations
from typing import Any, Dict, Type
import json
from pathlib import Path
from Code.Assets.Tools.core.artifact import Artifact

# Map artifact class name → Data subfolder
DEFAULT_FOLDERS = {
    "RawTextArtifact":       ("Data", "Primary", "filings"),
    "ChunksArtifact":        ("Data", "Secondary", "chunks"),
    "RoutedChunksArtifact":  ("Data", "Secondary", "routed"),
    "QualResultsArtifact":   ("Data", "Secondary", "qual_results"),
    "QuantResultsArtifact":  ("Data", "Secondary", "quant_results"),
    "SummaryArtifact":       ("Data", "Outputs", "Artifacts"),
}

def save_artifact(art: Artifact, filename: str | None = None) -> Path:
    cls = type(art).__name__
    parts = DEFAULT_FOLDERS.get(cls)
    if not parts:
        raise ValueError(f"No folder mapping for artifact type {cls}")
    base = Path(*parts)
    base.mkdir(parents=True, exist_ok=True)
    if filename is None:
        filename = f"{cls}.json"
    path = base / filename
    with path.open("w", encoding="utf-8") as f:
        json.dump(art.to_dict(), f, indent=2)
    return path

def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)
