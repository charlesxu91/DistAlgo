from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, List, Tuple


def load_edges_csv(path: Path, src_column: str = "src", dst_column: str = "dst") -> List[Tuple[int, int]]:
    edges = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            edges.append((int(row[src_column]), int(row[dst_column])))
    return edges


def load_json_dataset(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))
